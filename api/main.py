import os
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add the root directory to the python path so we can import from lib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import extract
from sqlalchemy.orm import Session

from config.resume_parser import parse_resume
from lib.db import Job, SessionLocal, get_resume_document, save_resume_document
from lib.job_scorer import score_job

app = FastAPI(title="Job Agent API")
_resume_jobs: dict[str, dict] = {}
_resume_jobs_lock = threading.Lock()

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_URLS",
        "https://ramlal-blush.vercel.app,http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class JobResponse(BaseModel):
    id: int
    score: Optional[float] = 0.0
    auto_apply_ready: Optional[bool] = False
    scored_on: Optional[str] = ""
    title: Optional[str] = ""
    company: Optional[str] = ""
    reasons: Optional[str] = ""
    snippet: Optional[str] = ""
    url: Optional[str] = ""
    applied: Optional[bool] = False
    status: Optional[str] = "New"
    applied_at: Optional[datetime] = None
    date_found: Optional[datetime] = None
    agent_failure_reason: Optional[str] = None
    retry_count: Optional[int] = 0
    last_attempted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


def _resume_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resume.pdf"
    )


def _job_for_scoring(job: Job) -> dict:
    return {
        "title": job.title or "",
        "company": job.company or "",
        "url": job.url or "",
        "snippet": job.snippet or job.reasons or "",
    }


def _set_resume_job(job_id: str, **updates):
    with _resume_jobs_lock:
        _resume_jobs[job_id].update(updates)


def _score_one_job(job_data: dict, resume_profile: dict) -> tuple[int, dict | None, str | None]:
    try:
        return job_data["id"], score_job(job_data, resume_profile, retries=1), None
    except Exception as exc:
        return job_data["id"], None, str(exc)


def _process_resume_upload(job_id: str, resume_bytes: bytes):
    """Parse and re-score outside the request so uploads never block the API."""
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(resume_bytes)
        _set_resume_job(job_id, status="parsing", message="Parsing your resume…")
        resume_profile = parse_resume(str(temporary_path))
        save_resume_document(resume_bytes)

        db = SessionLocal()
        try:
            jobs = db.query(Job).order_by(Job.score.desc()).all()
            job_data = [_job_for_scoring(job) | {"id": job.id} for job in jobs]
            _set_resume_job(
                job_id,
                status="rescoring",
                message=f"Refreshing {len(job_data)} job ratings…",
                total=len(job_data),
                completed=0,
            )

            updated_ids = set()
            failed_jobs = []
            completed = 0
            with ThreadPoolExecutor(max_workers=min(4, max(1, len(job_data)))) as executor:
                futures = [
                    executor.submit(_score_one_job, data, resume_profile)
                    for data in job_data
                ]
                for future in as_completed(futures):
                    job_id_result, rescored, error = future.result()
                    completed += 1
                    if rescored:
                        job = db.query(Job).filter(Job.id == job_id_result).first()
                        if job:
                            job.score = rescored.get("score", job.score)
                            job.reasons = rescored.get("reasons", job.reasons)
                            job.scored_on = "resume_refresh"
                            updated_ids.add(job.id)
                    else:
                        failed_jobs.append({"id": job_id_result, "error": error})
                    _set_resume_job(
                        job_id,
                        completed=completed,
                        message=f"Refreshing job ratings… ({completed}/{len(job_data)})",
                    )

            db.commit()
            updated_jobs = [
                db.query(Job).filter(Job.id == updated_id).first()
                for updated_id in updated_ids
            ]
            _set_resume_job(
                job_id,
                status="completed",
                message=f"{len(updated_jobs)} job ratings updated.",
                resume=resume_profile,
                updated_count=len(updated_jobs),
                failed_count=len(failed_jobs),
                failed_jobs=failed_jobs,
                jobs=[
                    JobResponse.model_validate(job).model_dump()
                    for job in updated_jobs
                    if job
                ],
            )
        finally:
            db.close()
    except Exception as exc:
        _set_resume_job(job_id, status="failed", message=str(exc))
    finally:
        if "temporary_path" in locals() and temporary_path.exists():
            temporary_path.unlink()


@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return {"status": "ok"}


@app.get("/api/jobs", response_model=list[JobResponse])
def get_jobs(
    db: Session = Depends(get_db),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    month: Optional[str] = None,
    status: Optional[str] = None,
):
    """Fetch jobs sorted by score descending, with optional filters."""
    query = db.query(Job)

    if date_from:
        query = query.filter(Job.date_found >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(
            Job.date_found <= datetime.fromisoformat(date_to + "T23:59:59")
        )
    if month:
        year, mon = month.split("-")
        query = query.filter(
            extract("year", Job.date_found) == int(year),
            extract("month", Job.date_found) == int(mon),
        )
    if status:
        query = query.filter(Job.status == status)

    jobs = query.order_by(Job.score.desc()).all()
    return jobs


@app.put("/api/jobs/{job_id}/apply")
def mark_job_applied(job_id: int, db: Session = Depends(get_db)):
    """Toggle the 'applied' boolean of a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.applied = not job.applied
    db.commit()

    return {"status": "success", "applied": job.applied}


VALID_STATUSES = [
    "New",
    "Saved",
    "Applied",
    "Interview",
    "Rejected",
    "Offer",
    "Agent Applied",
    "Agent Failed",
]


@app.put("/api/jobs/{job_id}/status", response_model=JobResponse)
def update_job_status(job_id: int, update: StatusUpdate, db: Session = Depends(get_db)):
    """Update the workflow status of a job."""
    if update.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of {VALID_STATUSES}",
        )
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = update.status
    if update.status == "Applied" and job.applied_at is None:
        job.applied_at = datetime.utcnow()

    db.commit()
    db.refresh(job)
    return job


@app.delete("/api/jobs/{job_id}")
def discard_job(job_id: int, db: Session = Depends(get_db)):
    """Permanently delete a job (expired or unwanted)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"status": "deleted", "id": job_id}


@app.get("/api/resume")
def download_resume():
    """Download the candidate's resume PDF."""
    resume = get_resume_document()
    if resume:
        return Response(
            content=resume.data,
            media_type=resume.content_type,
            headers={"Content-Disposition": f'inline; filename="{resume.filename}"'},
        )
    file_path = _resume_path()
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(
        path=file_path, filename="resume.pdf", media_type="application/pdf"
    )


@app.post("/api/resume", status_code=202)
async def upload_resume(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    """Accept a resume quickly and process parsing/re-scoring in the background."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF resumes are supported")

    chunks = []
    total_bytes = 0
    while chunk := await file.read(1024 * 1024):
        total_bytes += len(chunk)
        if total_bytes > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413, detail="Resume must be 10 MB or smaller"
            )
        chunks.append(chunk)
    await file.close()
    resume_bytes = b"".join(chunks)

    job_id = uuid.uuid4().hex
    with _resume_jobs_lock:
        _resume_jobs[job_id] = {
            "status": "queued",
            "message": "Resume uploaded. Processing will start shortly…",
            "total": 0,
            "completed": 0,
        }
    background_tasks.add_task(_process_resume_upload, job_id, resume_bytes)
    return {"status": "queued", "job_id": job_id}


@app.get("/api/resume/status/{job_id}")
def resume_status(job_id: str):
    with _resume_jobs_lock:
        status = _resume_jobs.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Resume processing job not found")
    return status

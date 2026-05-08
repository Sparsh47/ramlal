import os
import sys

# Add the root directory to the python path so we can import from lib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import extract
from sqlalchemy.orm import Session

from lib.db import Job, SessionLocal

app = FastAPI(title="Job Agent API")

# Allow requests from our frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ramlal-blush.vercel.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
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
    url: Optional[str] = ""
    applied: Optional[bool] = False
    status: Optional[str] = "New"
    applied_at: Optional[datetime] = None
    date_found: Optional[datetime] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


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


VALID_STATUSES = ["New", "Saved", "Applied", "Interview", "Rejected", "Offer"]


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
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resume.pdf"
    )
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(
        path=file_path, filename="resume.pdf", media_type="application/pdf"
    )

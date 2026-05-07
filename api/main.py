import os
import sys

# Add the root directory to the python path so we can import from lib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from lib.db import SessionLocal, Job
from pydantic import BaseModel

app = FastAPI(title="Job Agent API")

# Allow requests from our frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual frontend URL
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

# Define Pydantic models for responses
class JobResponse(BaseModel):
    id: int
    score: float
    auto_apply_ready: bool
    scored_on: str
    title: str
    company: str
    reasons: str
    url: str
    applied: bool

    class Config:
        from_attributes = True

@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return {"status": "ok"}

@app.get("/api/jobs", response_model=list[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    """Fetch all jobs, sorted by score descending."""
    jobs = db.query(Job).order_by(Job.score.desc()).all()
    return jobs

@app.put("/api/jobs/{job_id}/apply")
def mark_job_applied(job_id: int, db: Session = Depends(get_db)):
    """Toggle the 'applied' status of a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Toggle the status
    job.applied = not job.applied
    db.commit()
    
    return {"status": "success", "applied": job.applied}

from fastapi.responses import FileResponse

@app.get("/api/resume")
def download_resume():
    """Download the candidate's resume PDF."""
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resume.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(path=file_path, filename="Resume.pdf", media_type="application/pdf")

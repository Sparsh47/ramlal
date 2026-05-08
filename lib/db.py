import os
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise EnvironmentError(
        "DATABASE_URL is not set. Add it to your .env file.\n"
        "Get it from: Supabase → project → Settings → Database → Connection string → URI\n"
        "It should look like: postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres"
    )

# Supabase requires SSL — add sslmode=require if not already in the URL
if "supabase" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float)
    auto_apply_ready = Column(Boolean, default=False)
    scored_on = Column(String)
    title = Column(String)
    company = Column(String)
    reasons = Column(Text)
    url = Column(String, unique=True, index=True)
    date_found = Column(DateTime, default=datetime.utcnow)
    applied = Column(Boolean, default=False)
    status = Column(String, default="New")
    applied_at = Column(DateTime, nullable=True)
    agent_failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    last_attempted_at = Column(DateTime, nullable=True)


def run_migrations():
    """Alembic-free migrations: adds new columns to existing tables if they don't exist."""
    with engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'New'"
            )
        )
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS applied_at TIMESTAMP")
        )
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS agent_failure_reason TEXT")
        )
        conn.execute(
            text(
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_attempted_at TIMESTAMP"
            )
        )
        conn.commit()


# Create tables then apply any outstanding column-level migrations
Base.metadata.create_all(bind=engine)
run_migrations()


def get_existing_urls_db() -> set[str]:
    """Returns a set of URLs already present in the database."""
    session = SessionLocal()
    try:
        urls = session.query(Job.url).all()
        return {u[0] for u in urls if u[0]}
    finally:
        session.close()


def save_to_db(jobs: list[dict]):
    """Saves new jobs to the Postgres database."""
    session = SessionLocal()
    existing_urls = get_existing_urls_db()
    added_count = 0

    try:
        for job_data in jobs:
            url = job_data.get("url")
            if url in existing_urls:
                continue

            new_job = Job(
                score=job_data.get("score"),
                auto_apply_ready=job_data.get("auto_apply_ready", False),
                scored_on=job_data.get("scored_on", "unknown"),
                title=job_data.get("title", ""),
                company=job_data.get("company", ""),
                reasons=job_data.get("reasons", ""),
                url=url,
                date_found=datetime.utcnow(),
            )
            session.add(new_job)
            existing_urls.add(url)
            added_count += 1

        session.commit()
        print(
            f"Appended {added_count} new jobs to Postgres database (Skipped {len(jobs) - added_count} duplicates)"
        )
    except Exception as e:
        session.rollback()
        print(f"Database error: {e}")
    finally:
        session.close()


def get_eligible_jobs() -> list[dict]:
    """
    Return jobs that are ready for the agent to attempt applying.
    Criteria: status = 'New' AND retry_count < 3
    Ordered by score descending so the best matches are attempted first.
    Returns plain dicts (not SQLAlchemy objects) so they are safe to use
    outside of a session context.
    """
    session = SessionLocal()
    try:
        jobs = (
            session.query(Job)
            .filter(Job.status == "New", Job.retry_count < 3)
            .order_by(Job.score.desc())
            .all()
        )
        # Convert each ORM object to a plain dict before closing the session
        return [
            {
                "id": job.id,
                "url": job.url,
                "title": job.title,
                "company": job.company,
                "score": job.score,
                "reasons": job.reasons,
                "scored_on": job.scored_on,
                "auto_apply_ready": job.auto_apply_ready,
                "retry_count": job.retry_count,
                "status": job.status,
                "date_found": job.date_found,
                "applied_at": job.applied_at,
                "last_attempted_at": job.last_attempted_at,
                "agent_failure_reason": job.agent_failure_reason,
            }
            for job in jobs
        ]
    finally:
        session.close()


def mark_agent_applied(job_id: int) -> None:
    """
    Mark a job as successfully applied to by the agent.
    - Sets status to 'Agent Applied'
    - Stamps applied_at only on the first application (preserves original if already set)
    - Always updates last_attempted_at to now
    """
    session = SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "Agent Applied"
        job.last_attempted_at = datetime.utcnow()
        # Only stamp applied_at the very first time — never overwrite an existing timestamp
        if job.applied_at is None:
            job.applied_at = datetime.utcnow()

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def mark_agent_failed(job_id: int, reason: str) -> None:
    """
    Mark a job as failed by the agent.
    - Sets status to 'Agent Failed'
    - Stores the failure reason string
    - Increments retry_count by 1 (reads current value, never hardcodes)
    - Stamps last_attempted_at to now
    """
    session = SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "Agent Failed"
        job.agent_failure_reason = reason
        job.retry_count = (job.retry_count or 0) + 1
        job.last_attempted_at = datetime.utcnow()

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

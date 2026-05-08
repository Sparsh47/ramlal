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

# Default to the local docker-compose postgres credentials
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://jobagent:password@localhost:5432/jobsdb"
)

engine = create_engine(DATABASE_URL)
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

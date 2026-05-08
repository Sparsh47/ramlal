"""
test_cover_letter.py

Smoke-test for generate_cover_letter() against real jobs from the database.

Run from the project root:
    python test_cover_letter.py

What this script does:
  1. Fetches eligible jobs from the DB (status='New', retry_count < 3)
  2. Takes the first 3 (or fewer if fewer exist)
  3. Generates a cover letter for each job using a hardcoded sample resume
  4. Prints each cover letter with a clear separator, plus a word-count summary
  5. Errors on individual jobs are caught and reported without stopping the rest
"""

import os
import sys

# Ensure the project root is on the path so sibling packages (lib/, config/) import cleanly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from lib.cover_letter import generate_cover_letter
from lib.db import get_eligible_jobs

# ---------------------------------------------------------------------------
# Hardcoded sample resume — realistic enough to produce good cover letters
# without needing to parse the actual PDF
# ---------------------------------------------------------------------------

SAMPLE_RESUME = {
    "name": "Sparsh Yagnik",
    "current_role": "Full Stack Developer",
    "experience_level": "2 years",
    "location": "Delhi, India",
    "skills": {
        "languages": ["TypeScript", "Python", "JavaScript"],
        "frameworks": [
            "React",
            "Next.js",
            "Node.js",
            "FastAPI",
            "React Native",
            "Expo",
        ],
        "ai_ml": [
            "LangChain",
            "OpenAI API",
            "RAG pipelines",
            "vector databases",
            "Groq",
        ],
        "infrastructure": ["Docker", "PostgreSQL", "Supabase", "Vercel"],
        "concepts": ["REST APIs", "websockets", "prompt engineering"],
    },
    "projects": [
        {
            "name": "Ramlal — AI Job Agent",
            "outcome": "automated job discovery and scoring pipeline that scrapes 4 job boards daily, uses an LLM to score each listing against my resume, and saves top matches to a PostgreSQL DB — reduced manual job hunting from hours to zero",
            "tech": ["Python", "FastAPI", "LangChain", "PostgreSQL", "React", "Docker"],
        },
        {
            "name": "RAG document Q&A system",
            "outcome": "built a retrieval-augmented generation pipeline that ingested 500+ page PDFs, chunked and embedded them into a vector database, and answered natural language queries with source citations — reduced document search time by ~80%",
            "tech": ["LangChain", "OpenAI API", "Pinecone", "FastAPI", "Python"],
        },
        {
            "name": "Real-time collaboration app",
            "outcome": "built a multi-user whiteboard app with websocket-based sync, supporting 50+ concurrent users with sub-100ms latency, deployed on Vercel + Railway",
            "tech": ["Next.js", "TypeScript", "Node.js", "WebSockets", "PostgreSQL"],
        },
        {
            "name": "Cross-platform fitness tracker",
            "outcome": "shipped a React Native app for iOS and Android with offline-first sync, push notifications, and a Node.js backend — 200+ active users on TestFlight",
            "tech": ["React Native", "Expo", "TypeScript", "Node.js", "Supabase"],
        },
    ],
    "experience": [
        {
            "role": "Full Stack Developer",
            "company": "Freelance / Independent",
            "bullets": [
                "Built and shipped 4 production applications across web and mobile, handling everything from architecture to deployment",
                "Designed and integrated LLM-powered features using LangChain and OpenAI API, including a RAG pipeline that processed 500+ page documents",
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 72


def word_count(text: str) -> int:
    return len(text.split())


def print_job_header(index: int, job: dict) -> None:
    print(f"\n{SEPARATOR}")
    print(
        f"  Job {index} — {job.get('title', 'Unknown Title')} @ {job.get('company', 'Unknown Company')}"
    )
    print(f"  Score: {job.get('score', 'N/A')}  |  ID: {job.get('id', 'N/A')}")
    print(SEPARATOR)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("\nFetching eligible jobs from database...")
    all_jobs = get_eligible_jobs()

    if not all_jobs:
        print("No eligible jobs found in the database (status='New', retry_count < 3).")
        print("Seed some jobs first via main.py or migrate_excel.py.")
        return

    jobs = all_jobs[:3]
    print(
        f"Found {len(all_jobs)} eligible job(s). Testing with the first {len(jobs)}.\n"
    )

    word_counts: list[tuple[str, int]] = []  # (label, word_count)

    for i, job in enumerate(jobs, start=1):
        label = f"{job.get('title', 'Unknown')} @ {job.get('company', 'Unknown')}"
        print_job_header(i, job)

        try:
            cover_letter = generate_cover_letter(job, SAMPLE_RESUME)
            print(cover_letter)

            wc = word_count(cover_letter)
            word_counts.append((label, wc))

        except RuntimeError as exc:
            print(f"\n[ERROR] Cover letter generation failed for job {i}:")
            print(f"  {exc}")
            word_counts.append((label, -1))

        except Exception as exc:
            print(f"\n[ERROR] Unexpected error for job {i} ({label}):")
            print(f"  {type(exc).__name__}: {exc}")
            word_counts.append((label, -1))

    # ── Word count summary ────────────────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    print("  WORD COUNT SUMMARY")
    print(SEPARATOR)
    for label, wc in word_counts:
        if wc >= 0:
            status = "OK" if wc < 300 else "OVER LIMIT"
            print(f"  [{status:^9}]  {wc:>3} words  —  {label}")
        else:
            print(f"  [  FAILED ]  ---        —  {label}")
    print(SEPARATOR)
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
test_apply.py — Dry-run test of the complete apply pipeline.

Tests the full flow without actually submitting any application:
  Step 1 — Resume parsing          (real — reads resume.pdf via LLM)
  Step 2 — Candidate dict assembly (real — env vars + parsed resume)
  Step 3 — DB: get_eligible_jobs() (real — hits your local Postgres)
  Step 4 — Platform detection      (real — is_supported / get_apply_url)
  Step 5 — Field inspection        (real — Hermes browser visits the page)
  Step 6 — Cover letter generation (real — LLM generates the letter)
  Step 7 — Fill prompt preview     (real — builds the exact prompt that would be sent)
  Step 8 — SKIPS actual submission (dry-run — prints the prompt instead)
  Step 9 — DB marking test         (real — marks one job Agent Failed, one Agent Applied,
                                    verifies the DB, then resets both back to New)

Run from the project root:
    python test_apply.py

Flags:
    --job-id <id>    Test against a specific job ID instead of the top eligible job
    --limit <n>      Test against the first N eligible jobs (default: 1)
    --skip-resume    Skip resume parsing, use the hardcoded SAMPLE_RESUME instead
                     (faster if you just want to test the pipeline, not the LLM parser)
"""

import argparse
import os
import sys
import traceback
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv()

# ── Import everything from apply.py and lib/ ──────────────────────────────────
import apply as apply_module
from apply import (
    CANDIDATE,
    HERMES_BIN,
    HERMES_MODEL,
    RESUME_PATH,
    build_fill_prompt,
    get_apply_url,
    inspect_fields,
    is_supported,
)
from config.resume_parser import parse_resume
from lib.cover_letter import generate_cover_letter
from lib.db import (
    Job,
    SessionLocal,
    get_eligible_jobs,
    mark_agent_applied,
    mark_agent_failed,
)

# ── Sample resume fallback (used with --skip-resume) ─────────────────────────
SAMPLE_RESUME = {
    "name": "Sparsh Yagnik",
    "email": os.getenv("CANDIDATE_EMAIL", ""),
    "phone": os.getenv("CANDIDATE_PHONE", ""),
    "current_role": "Full Stack Developer",
    "experience_level": "2 years",
    "location": "Delhi, India",
    "skills": {
        "languages": ["TypeScript", "Python", "JavaScript"],
        "frameworks": ["React", "Next.js", "Node.js", "FastAPI", "React Native"],
        "ai_ml": ["LangChain", "OpenAI API", "RAG pipelines", "vector databases"],
        "infrastructure": ["Docker", "PostgreSQL", "Supabase", "Vercel"],
        "concepts": ["REST APIs", "websockets", "prompt engineering"],
    },
    "projects": [
        {
            "name": "Ramlal — AI Job Agent",
            "outcome": "automated job discovery pipeline scraping 4 job boards daily, "
            "LLM-scoring each listing against my resume, reduced manual job "
            "hunting from hours to zero",
            "tech": ["Python", "FastAPI", "LangChain", "PostgreSQL", "React", "Docker"],
        },
        {
            "name": "RAG document Q&A system",
            "outcome": "ingested 500+ page PDFs into a vector DB, answered natural "
            "language queries with source citations, reduced search time ~80%",
            "tech": ["LangChain", "OpenAI API", "Pinecone", "FastAPI", "Python"],
        },
        {
            "name": "Real-time collaboration app",
            "outcome": "multi-user whiteboard with websocket sync, 50+ concurrent users, "
            "sub-100ms latency",
            "tech": ["Next.js", "TypeScript", "Node.js", "WebSockets", "PostgreSQL"],
        },
        {
            "name": "Cross-platform fitness tracker",
            "outcome": "React Native app for iOS + Android with offline sync, "
            "push notifications, 200+ TestFlight users",
            "tech": ["React Native", "Expo", "TypeScript", "Node.js", "Supabase"],
        },
    ],
    "experience": [
        {
            "role": "Full Stack Developer",
            "company": "Freelance / Independent",
            "bullets": [
                "Shipped 4 production apps across web and mobile end-to-end",
                "Built LLM-powered features with LangChain + OpenAI API including a RAG "
                "pipeline over 500+ page documents",
            ],
        }
    ],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

SEP = "=" * 68
SEP2 = "-" * 68

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
INFO = "\033[94mINFO\033[0m"
WARN = "\033[93mWARN\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    tag = PASS if condition else FAIL
    print(f"  [{tag}] {name}" + (f"  — {detail}" if detail else ""))
    results.append((name, condition, detail))
    return condition


def section(title: str) -> None:
    print(f"\n{SEP}\n  {title}\n{SEP}")


def fetch_job_from_db(job_id: int) -> Job | None:
    session = SessionLocal()
    try:
        return session.query(Job).filter(Job.id == job_id).first()
    finally:
        session.close()


def reset_job_to_new(job_id: int) -> None:
    """Reset a job back to New / retry_count=0 after DB marking tests."""
    session = SessionLocal()
    try:
        job = session.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "New"
            job.retry_count = 0
            job.agent_failure_reason = None
            job.applied_at = None
            job.last_attempted_at = None
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Test steps ────────────────────────────────────────────────────────────────


def test_step1_resume(skip_resume: bool) -> dict:
    section("STEP 1 — Resume Parsing")

    if skip_resume:
        print(f"  [{INFO}] --skip-resume flag set, using hardcoded SAMPLE_RESUME")
        CANDIDATE.update(SAMPLE_RESUME)
    else:
        print(f"  Parsing {RESUME_PATH} via LLM...")
        if not os.path.exists(RESUME_PATH):
            check("resume.pdf exists", False, f"not found at {RESUME_PATH}")
            print("  Falling back to SAMPLE_RESUME")
            CANDIDATE.update(SAMPLE_RESUME)
        else:
            resume_data = parse_resume(RESUME_PATH)
            CANDIDATE.update(resume_data)
            check(
                "resume parsed successfully",
                bool(CANDIDATE.get("name")),
                f"name={CANDIDATE.get('name')}",
            )

    # Supplement contact fields from env
    CANDIDATE.setdefault("email", os.getenv("CANDIDATE_EMAIL", "test@example.com"))
    CANDIDATE.setdefault("phone", os.getenv("CANDIDATE_PHONE", "+91-9999999999"))
    CANDIDATE.setdefault(
        "linkedin",
        os.getenv("CANDIDATE_LINKEDIN", "https://linkedin.com/in/sparshyagnik"),
    )
    CANDIDATE.setdefault(
        "github", os.getenv("CANDIDATE_GITHUB", "https://github.com/sparshy")
    )
    CANDIDATE.setdefault("portfolio", os.getenv("CANDIDATE_PORTFOLIO", ""))
    CANDIDATE.setdefault(
        "current_company",
        os.getenv("CANDIDATE_CURRENT_COMPANY", "Freelance / Independent"),
    )
    CANDIDATE.setdefault(
        "notice_period", os.getenv("CANDIDATE_NOTICE_PERIOD", "0-15 Days")
    )

    # Ensure projects + experience are set (resume_parser doesn't extract these yet)
    CANDIDATE.setdefault("projects", SAMPLE_RESUME["projects"])
    CANDIDATE.setdefault("experience", SAMPLE_RESUME["experience"])

    print(f"\n  Candidate assembled:")
    print(f"    Name:       {CANDIDATE.get('name')}")
    print(
        f"    Role:       {CANDIDATE.get('current_role') or CANDIDATE.get('experience_level')}"
    )
    print(f"    Location:   {CANDIDATE.get('location')}")
    print(f"    Email:      {CANDIDATE.get('email')}")
    print(f"    Phone:      {CANDIDATE.get('phone')}")
    print(f"    LinkedIn:   {CANDIDATE.get('linkedin')}")
    print(f"    GitHub:     {CANDIDATE.get('github')}")
    skills = CANDIDATE.get("skills", {})
    print(f"    Languages:  {skills.get('languages', [])}")
    print(f"    Frameworks: {skills.get('frameworks', [])}")
    print(f"    AI/ML:      {skills.get('ai_ml', [])}")
    print(f"    Projects:   {[p['name'] for p in CANDIDATE.get('projects', [])]}")

    return CANDIDATE


def test_step2_db(job_id_override: int | None, limit: int) -> list[dict]:
    section("STEP 2 — DB: Fetch Eligible Jobs")

    all_jobs = get_eligible_jobs()
    auto_ready = [j for j in all_jobs if j.get("auto_apply_ready")]
    unsupported = [j for j in auto_ready if not is_supported(j["url"])]
    supported = [j for j in auto_ready if is_supported(j["url"])]

    check("get_eligible_jobs() returns a list", isinstance(all_jobs, list))
    check(
        "results are plain dicts (not ORM objs)",
        all(isinstance(j, dict) for j in all_jobs),
    )
    check(
        f"{len(auto_ready)} auto_apply_ready jobs found",
        len(auto_ready) > 0,
        f"total eligible: {len(all_jobs)}",
    )

    print(f"\n  Breakdown:")
    print(f"    Total eligible (New, retry<3):  {len(all_jobs)}")
    print(f"    auto_apply_ready=True:          {len(auto_ready)}")
    print(f"    Supported platform (Lever/GH):  {len(supported)}")
    print(f"    Unsupported (LinkedIn/other):   {len(unsupported)}")

    if unsupported:
        print(f"\n  [{WARN}] Unsupported platform jobs (will be skipped in real run):")
        for j in unsupported[:3]:
            print(f"    - [{j['id']}] {j['title']} @ {j['company']}  |  {j['url']}")

    # Select jobs to test
    if job_id_override:
        jobs = [j for j in all_jobs if j["id"] == job_id_override]
        if not jobs:
            print(f"  [{WARN}] Job ID {job_id_override} not found in eligible jobs.")
            print(f"  Falling back to top {limit} eligible job(s).")
            jobs = supported[:limit] if supported else auto_ready[:limit]
    else:
        jobs = supported[:limit] if supported else auto_ready[:limit]

    if not jobs:
        print(f"\n  [{WARN}] No jobs to test. Exiting pipeline test.")
        return []

    print(f"\n  Jobs selected for pipeline test ({len(jobs)}):")
    for j in jobs:
        platform = (
            "Lever"
            if "lever.co" in j["url"]
            else "Greenhouse"
            if "greenhouse.io" in j["url"]
            else "Other"
        )
        print(f"    [{j['id']}] {j['title']} @ {j['company']}")
        print(
            f"           score={j['score']}  platform={platform}  retry={j['retry_count']}"
        )
        print(f"           url={j['url']}")

    return jobs


def test_step3_platform(job: dict) -> str | None:
    section(f"STEP 3 — Platform Detection  [job {job['id']}]")

    url = job["url"]
    supported = is_supported(url)
    check("platform is supported", supported, url)

    if not supported:
        print(f"  [{WARN}] Skipping unsupported platform: {url}")
        return None

    apply_url = get_apply_url(url)
    is_lever = "lever.co" in url
    is_greenhouse = "greenhouse.io" in url

    if is_lever:
        check(
            "Lever URL gets /apply appended",
            apply_url == url.rstrip("/") + "/apply",
            apply_url,
        )
    elif is_greenhouse:
        check(
            "Greenhouse URL unchanged (form on same page)", apply_url == url, apply_url
        )

    print(f"  Apply URL: {apply_url}")
    return apply_url


def test_step4_fields(apply_url: str, job: dict) -> list[str]:
    section(f"STEP 4 — Field Inspection via Hermes  [job {job['id']}]")

    print(f"  Asking Hermes to visit: {apply_url}")
    print(f"  Model: {HERMES_MODEL}")
    print(f"  (this makes a real browser call — may take 15-30s)\n")

    fields = inspect_fields(apply_url)

    check("fields returned", len(fields) > 0, f"{len(fields)} fields")
    check("fields are strings", all(isinstance(f, str) for f in fields))
    check(
        "at least name/email found",
        any("name" in f.lower() or "email" in f.lower() for f in fields),
        str(fields[:4]),
    )

    print(f"\n  Fields found ({len(fields)}):")
    for i, f in enumerate(fields, 1):
        print(f"    {i:>2}. {f}")

    return fields


def test_step5_cover_letter(job: dict) -> str:
    section(f"STEP 5 — Cover Letter Generation  [job {job['id']}]")

    print(f"  Job:    {job['title']} @ {job['company']}")
    print(f"  Score:  {job['score']}")
    print(f"  (LLM call — may take 5-10s)\n")

    cover_letter = generate_cover_letter(job, CANDIDATE)
    word_count = len(cover_letter.split())

    check("cover letter generated", len(cover_letter) > 50)
    check("word count 200-300", 200 <= word_count <= 310, f"{word_count} words")
    check(
        "starts with 'Hiring Team,'",
        cover_letter.strip().startswith("Hiring Team,"),
        cover_letter[:40],
    )
    check(
        "ends with candidate first name",
        cover_letter.strip().split("\n")[-1].strip()
        in CANDIDATE.get("name", "Sparsh").split(),
        cover_letter.strip()[-20:],
    )

    print(f"\n  Cover letter ({word_count} words):\n")
    print(SEP2)
    print(cover_letter)
    print(SEP2)

    return cover_letter


def test_step6_fill_prompt(
    apply_url: str, fields: list[str], cover_letter: str, job: dict
) -> None:
    section(f"STEP 6 — Fill Prompt Preview  [job {job['id']}]")

    print("  Building the exact prompt that would be sent to Hermes for form filling.")
    print("  (DRY RUN — this is NOT sent anywhere)\n")

    prompt = build_fill_prompt(apply_url, fields, cover_letter)

    # Checks on the prompt itself
    check("prompt contains apply URL", apply_url in prompt)
    check("prompt contains candidate name", CANDIDATE.get("name", "") in prompt)
    check("prompt contains candidate email", CANDIDATE.get("email", "") in prompt)
    check("prompt contains resume path", RESUME_PATH in prompt)
    check("prompt contains cover letter", cover_letter[:50] in prompt)
    check("prompt contains SUCCESS sentinel", "SUCCESS" in prompt)
    check("prompt contains CAPTCHA sentinel", "CAPTCHA_BLOCKED" in prompt)
    check("prompt contains FAILED sentinel", "FAILED" in prompt)

    # Check that every field has an entry in the prompt
    unmapped = [f for f in fields if f not in prompt]
    check(
        "all fields appear in prompt",
        len(unmapped) == 0,
        f"unmapped: {unmapped}" if unmapped else "all mapped",
    )

    print(f"\n  Full fill prompt ({len(prompt)} chars):\n")
    print(SEP2)
    print(prompt)
    print(SEP2)


def test_step7_db_marking(job: dict) -> None:
    section(f"STEP 7 — DB Marking Test  [job {job['id']}]")

    job_id = job["id"]
    original_retry = job["retry_count"]

    print("  Testing mark_agent_failed() ...")
    before = datetime.utcnow()
    mark_agent_failed(job_id, "dry-run test failure — not a real error")
    after = datetime.utcnow()

    db_job = fetch_job_from_db(job_id)
    check("status = 'Agent Failed'", db_job.status == "Agent Failed", db_job.status)
    check(
        "agent_failure_reason stored",
        "dry-run test failure" in (db_job.agent_failure_reason or ""),
        db_job.agent_failure_reason,
    )
    check(
        "retry_count incremented",
        db_job.retry_count == original_retry + 1,
        f"{original_retry} → {db_job.retry_count}",
    )
    check("last_attempted_at stamped", db_job.last_attempted_at is not None)
    if db_job.last_attempted_at:
        ts = (
            db_job.last_attempted_at.replace(tzinfo=None)
            if db_job.last_attempted_at.tzinfo
            else db_job.last_attempted_at
        )
        check(
            "last_attempted_at is recent",
            before <= ts <= after,
            str(db_job.last_attempted_at),
        )

    # Reset before testing applied
    print("\n  Resetting job to New for applied test ...")
    reset_job_to_new(job_id)

    print("\n  Testing mark_agent_applied() ...")
    before = datetime.utcnow()
    mark_agent_applied(job_id)
    after = datetime.utcnow()

    db_job = fetch_job_from_db(job_id)
    check("status = 'Agent Applied'", db_job.status == "Agent Applied", db_job.status)
    check("applied_at is set", db_job.applied_at is not None)
    if db_job.applied_at:
        ts = (
            db_job.applied_at.replace(tzinfo=None)
            if db_job.applied_at.tzinfo
            else db_job.applied_at
        )
        check("applied_at is recent", before <= ts <= after, str(db_job.applied_at))
    check("last_attempted_at is set", db_job.last_attempted_at is not None)

    # Reset back to New so we don't pollute real data
    print("\n  Resetting job back to New (cleaning up test state) ...")
    reset_job_to_new(job_id)
    db_job = fetch_job_from_db(job_id)
    check(
        "job reset to New successfully",
        db_job.status == "New" and db_job.retry_count == 0,
        f"status={db_job.status} retry={db_job.retry_count}",
    )


# ── Main ──────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dry-run test for the apply pipeline")
    p.add_argument(
        "--job-id", type=int, default=None, help="Test against a specific job ID"
    )
    p.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of eligible jobs to test (default: 1)",
    )
    p.add_argument(
        "--skip-resume",
        action="store_true",
        help="Skip resume PDF parsing, use hardcoded SAMPLE_RESUME",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    start = datetime.utcnow()

    print(f"\n{SEP}")
    print(f"  Ramlal Apply Pipeline — Dry-Run Test")
    print(f"  {start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Hermes model: {HERMES_MODEL}")
    print(f"  Hermes bin:   {HERMES_BIN}")
    print(f"  Resume:       {RESUME_PATH}")
    print(SEP)

    # Pre-flight: check Hermes binary exists
    if not os.path.exists(HERMES_BIN):
        print(f"\n  [{FAIL}] Hermes binary not found at {HERMES_BIN}")
        print(f"  Install Hermes or update HERMES_BIN in apply.py")
        sys.exit(1)

    # ── Run steps ─────────────────────────────────────────────────────────────
    try:
        test_step1_resume(args.skip_resume)
    except Exception as e:
        print(f"\n  [ERROR] Resume step failed: {e}")
        print("  Falling back to SAMPLE_RESUME")
        CANDIDATE.update(SAMPLE_RESUME)

    jobs = test_step2_db(args.job_id, args.limit)

    if not jobs:
        print(f"\n  [{WARN}] No eligible jobs found — nothing to test.")
        print("  Run main.py first to populate the DB, or check your DB connection.")
        sys.exit(0)

    # Run the full pipeline for each selected job
    for i, job in enumerate(jobs, 1):
        print(f"\n\n{'#' * 68}")
        print(f"#  PIPELINE TEST {i}/{len(jobs)} — Job ID {job['id']}")
        print(f"#  {job['title']} @ {job['company']}")
        print(f"{'#' * 68}")

        apply_url = test_step3_platform(job)
        if apply_url is None:
            print(f"  Skipping job {job['id']} — unsupported platform")
            continue

        try:
            fields = test_step4_fields(apply_url, job)
        except Exception as e:
            print(f"\n  [ERROR] Field inspection failed: {e}")
            traceback.print_exc()
            print(f"\n  Skipping steps 5-7 for job {job['id']}")
            continue

        try:
            cover_letter = test_step5_cover_letter(job)
        except Exception as e:
            print(f"\n  [ERROR] Cover letter failed: {e}")
            traceback.print_exc()
            cover_letter = (
                "Cover letter generation failed — would be retried in real run."
            )

        test_step6_fill_prompt(apply_url, fields, cover_letter, job)
        test_step7_db_marking(job)

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = (datetime.utcnow() - start).seconds
    mins, secs = divmod(elapsed, 60)
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print(f"\n{SEP}")
    print(f"  DRY-RUN COMPLETE  |  {mins}m {secs}s")
    print(f"  Checks: {passed}/{total} passed", end="")
    if failed:
        print(f"  |  {failed} failed:")
        for name, ok, detail in results:
            if not ok:
                print(f"    ✗ {name}" + (f" — {detail}" if detail else ""))
    else:
        print("  ✓")
    print(SEP)
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

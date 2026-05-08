#!/root/ramlal/.venv/bin/python
import os
import sys
import time
import traceback
from datetime import datetime

# ── Fix import paths so cron can find lib/ and config/ ───────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config.resume_parser import parse_resume
from config.tinyfish_client import fetch_job_details, search_jobs
from lib.db import get_existing_urls_db, save_to_db
from lib.job_scorer import score_all_jobs, score_job
from lib.query_builder import build_search_queries

RESUME_PATH = os.path.join(BASE_DIR, "resume.pdf")


def log(msg: str):
    """Print with a UTC timestamp prefix — makes cron.log easy to read."""
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}", flush=True)


def check_env():
    """Fail fast if required environment variables or files are missing."""
    missing = []
    for var in ("GROQ_API_KEY", "TINYFISH_API_KEY"):
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
    if not os.path.exists(RESUME_PATH):
        raise FileNotFoundError(f"Resume not found at {RESUME_PATH}")


def run():
    start = datetime.utcnow()
    log("=" * 60)
    log("Ramlal cron job started")
    log("=" * 60)

    # ── Pre-flight checks ─────────────────────────────────────────────────────
    check_env()
    log("Environment OK")

    # ── Step 1: Parse resume ──────────────────────────────────────────────────
    log("Parsing resume...")
    resume_data = parse_resume(RESUME_PATH)
    log(
        f"Resume parsed — {resume_data.get('name', 'unknown')} | "
        f"{resume_data.get('experience_level', '?')} | "
        f"{len(resume_data.get('skills', {}).get('languages', []))} languages"
    )

    # ── Step 2: Build search queries ──────────────────────────────────────────
    log("Building search queries...")
    queries = build_search_queries(resume_data)
    log(f"Generated {len(queries)} queries")
    for i, q in enumerate(queries, 1):
        log(f"  [{i}/{len(queries)}] {q}")

    # ── Step 3: Search for jobs ───────────────────────────────────────────────
    log("Searching for jobs...")
    all_jobs = []
    seen_urls = get_existing_urls_db()
    log(f"Loaded {len(seen_urls)} existing URLs from DB (will skip duplicates)")

    search_errors = 0
    for i, query in enumerate(queries, 1):
        try:
            results = search_jobs(query, num_results=5)
            new_for_query = 0
            for job in results:
                if job["url"] not in seen_urls:
                    seen_urls.add(job["url"])
                    all_jobs.append(job)
                    new_for_query += 1
            log(f"  [{i}/{len(queries)}] '{query}' → {new_for_query} new jobs")
        except Exception as e:
            search_errors += 1
            log(f"  [{i}/{len(queries)}] Search failed: {e}")
        time.sleep(13)

    log(
        f"Search complete — {len(all_jobs)} new unique listings "
        f"({search_errors} query errors)"
    )

    if not all_jobs:
        log("No new jobs found. Exiting early.")
        _print_summary(start, 0, 0, 0)
        return

    # ── Step 4: Phase 1 quick scoring ─────────────────────────────────────────
    log("Phase 1 — quick scoring on snippets...")
    quick_scored = score_all_jobs(all_jobs, resume_data)
    top_jobs = [j for j in quick_scored if j.get("score", 0) >= 6]
    log(f"Phase 1 complete — {len(top_jobs)}/{len(all_jobs)} jobs scored >= 6")

    if not top_jobs:
        log("No jobs passed Phase 1 filter. Exiting early.")
        _print_summary(start, len(all_jobs), 0, 0)
        return

    # ── Step 5: Phase 2 full fetch + re-score ────────────────────────────────
    log("Phase 2 — fetching full JD and re-scoring...")
    final_jobs = []
    fetch_ok = 0
    fetch_fail = 0

    for i, job in enumerate(top_jobs, 1):
        try:
            log(f"  [{i}/{len(top_jobs)}] {job.get('url', '?')}")
            fetch_result = fetch_job_details(job["url"])

            if fetch_result["fetch_success"]:
                job["snippet"] = fetch_result["content"][:3000]
                rescored = score_job(job, resume_data)
                rescored["auto_apply_ready"] = True
                rescored["scored_on"] = "full_jd"
                fetch_ok += 1
                if rescored.get("score", 0) >= 7:
                    final_jobs.append(rescored)
                    log(f"    ✓ score={rescored.get('score')} auto_apply=True → KEPT")
                else:
                    log(f"    ✗ score={rescored.get('score')} → below threshold")
            else:
                rescored = score_job(job, resume_data)
                rescored["auto_apply_ready"] = False
                rescored["scored_on"] = "snippet"
                fetch_fail += 1
                if rescored.get("score", 0) >= 7:
                    final_jobs.append(rescored)
                    log(
                        f"    ✓ score={rescored.get('score')} auto_apply=False (snippet) → KEPT"
                    )
                else:
                    log(f"    ✗ score={rescored.get('score')} → below threshold")
        except Exception as e:
            log(f"    ERROR processing job: {e}")
            traceback.print_exc()

        time.sleep(3)

    log(f"Phase 2 complete — {fetch_ok} full fetches, {fetch_fail} snippet fallbacks")
    log(f"{len(final_jobs)} high-quality jobs to save")

    # ── Step 6: Save to DB ────────────────────────────────────────────────────
    if final_jobs:
        log("Saving to database...")
        save_to_db(final_jobs)
    else:
        log("No jobs to save.")

    _print_summary(start, len(all_jobs), len(top_jobs), len(final_jobs))


def _print_summary(start: datetime, found: int, phase1: int, saved: int):
    elapsed = (datetime.utcnow() - start).seconds
    mins, secs = divmod(elapsed, 60)
    log("=" * 60)
    log(f"Run complete in {mins}m {secs}s")
    log(f"  Jobs found (new URLs):     {found}")
    log(f"  Passed Phase 1 (score>=6): {phase1}")
    log(f"  Saved to DB (score>=7):    {saved}")
    log("=" * 60)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

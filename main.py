#!/root/ramlal/.venv/bin/python
import os
import time

from config.resume_parser import parse_resume

# Always resolve paths relative to this file, not the working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from config.tinyfish_client import fetch_job_details, search_jobs
from lib.db import get_existing_urls_db, save_to_db
from lib.job_scorer import score_all_jobs, score_job
from lib.query_builder import build_search_queries


def run():
    print("Parsing resume...")
    resume_data = parse_resume(os.path.join(BASE_DIR, "resume.pdf"))

    print("Building search queries...")
    queries = build_search_queries(resume_data)
    print(f"Queries: {queries}")

    print("Searching for jobs...")
    all_jobs = []

    # Load existing URLs from Postgres to avoid re-processing duplicates
    seen_urls = get_existing_urls_db()
    initial_seen_count = len(seen_urls)
    if initial_seen_count > 0:
        print(f"Loaded {initial_seen_count} existing jobs to skip duplicates.")

    for i, query in enumerate(queries):
        print(f"  [{i + 1}/{len(queries)}] {query}")
        results = search_jobs(query, num_results=5)
        for job in results:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
        time.sleep(13)

    print(f"Found {len(all_jobs)} NEW unique listings (skipped duplicates)")

    # Phase 1 — quick score on snippet to narrow down
    print("Quick scoring...")
    quick_scored = score_all_jobs(all_jobs, resume_data)
    top_jobs = [j for j in quick_scored if j["score"] >= 6]
    print(f"{len(top_jobs)} jobs passed quick score filter")

    # Phase 2 — fetch full content and re-score top jobs
    print("Fetching full job details and re-scoring...")
    final_jobs = []
    for i, job in enumerate(top_jobs):
        print(f"  [{i + 1}/{len(top_jobs)}] Processing {job['url']}")

        fetch_result = fetch_job_details(job["url"])

        if fetch_result["fetch_success"]:
            # Re-score using full page content
            job["snippet"] = fetch_result["content"][:3000]
            rescored = score_job(job, resume_data)
            rescored["auto_apply_ready"] = True
            rescored["scored_on"] = "full_jd"
            if rescored["score"] >= 7:
                final_jobs.append(rescored)
        else:
            print(f"    Full fetch skipped/failed — re-scoring with snippet")
            rescored = score_job(job, resume_data)
            rescored["auto_apply_ready"] = False
            rescored["scored_on"] = "snippet"
            if rescored["score"] >= 7:
                final_jobs.append(rescored)

        time.sleep(3)  # small delay between fetches

    print(f"{len(final_jobs)} high-quality jobs after re-scoring")

    print("Saving to Postgres database...")
    save_to_db(final_jobs)
    print("Done.")


if __name__ == "__main__":
    run()

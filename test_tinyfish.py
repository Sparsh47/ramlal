from config.tinyfish_client import search_jobs, fetch_job_details

results = search_jobs("React Next.js TypeScript", num_results=5)
for r in results:
    print(r["title"])
    print(r["url"])
    print()
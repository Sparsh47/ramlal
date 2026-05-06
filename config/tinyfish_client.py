import os
import re
import html
import requests
import html2text
import trafilatura
from dotenv import load_dotenv

load_dotenv()

TINYFISH_API_KEY = os.getenv("TINYFISH_API_KEY")

# ── Search targets ────────────────────────────────────────────────────────────
# Ashby removed: their pages are fully JS-gated (returns 46 chars) with no public API.
# Greenhouse & Lever have open public APIs, so they're the best sources.
JOB_SITES = [
    "site:linkedin.com/jobs/view",
    "site:jobs.lever.co",
    "site:boards.greenhouse.io",
    "site:wellfound.com/jobs",
]

ATS_PATTERNS = [
    r'linkedin\.com/jobs/view/\d+',
    r'wellfound\.com/jobs/\d+',
    r'boards\.greenhouse\.io/.+/jobs/\d+',
    r'jobs\.lever\.co/.+/[0-9a-f-]{36}',
]

# Suffixes that point to SPA application forms, not the job description
_BAD_SUFFIXES = ('/application', '/apply', '/referral', '/share')

# Browser-like headers for direct scraping (LinkedIn, Wellfound)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Per-run cache: company slug → list of Lever postings (avoid re-fetching same company)
_lever_cache: dict[str, list] = {}


def normalize_url(url: str) -> str:
    """Strip non-listing suffixes and query params that point to SPA forms."""
    # Strip query strings from Lever URLs (e.g. ?lever-source=Indeed)
    if 'lever.co' in url and '?' in url:
        url = url.split('?')[0]
    for suffix in _BAD_SUFFIXES:
        if url.endswith(suffix):
            url = url[:-len(suffix)]
    return url


def is_individual_listing(url: str) -> bool:
    return any(re.search(p, url) for p in ATS_PATTERNS)


def search_jobs(query: str, num_results: int = 5) -> list[dict]:
    all_results = []
    seen_urls = set()

    for site in JOB_SITES:
        try:
            response = requests.get(
                "https://api.search.tinyfish.ai",
                headers={"X-API-Key": TINYFISH_API_KEY},
                params={"query": f"{query} {site}", "num_results": num_results},
                timeout=15,
            )
        except requests.exceptions.RequestException:
            continue

        if response.status_code == 429:
            break
        if not response.ok:
            continue

        for r in response.json().get("results", []):
            url = normalize_url(r.get("url", ""))
            if url not in seen_urls and is_individual_listing(url):
                seen_urls.add(url)
                all_results.append({
                    "title": r.get("title"),
                    "url": url,
                    "snippet": r.get("snippet"),
                })

    return all_results


# ── Platform-native fetchers ──────────────────────────────────────────────────

def _fetch_lever(url: str) -> str:
    """
    Use Lever's public postings API.
    URL: https://jobs.lever.co/{company}/{uuid}
    API: https://api.lever.co/v0/postings/{company} → find by id
    """
    match = re.search(r'lever\.co/([^/?#]+)/([0-9a-f-]{36})', url)
    if not match:
        raise Exception("Could not parse Lever URL")
    company, job_id = match.groups()

    # Cache per company to avoid redundant API calls
    if company not in _lever_cache:
        r = requests.get(
            f"https://api.lever.co/v0/postings/{company}",
            timeout=12,
        )
        r.raise_for_status()
        _lever_cache[company] = r.json()

    job = next((j for j in _lever_cache[company] if j.get("id") == job_id), None)
    if not job:
        raise Exception(f"Job {job_id} not found in {company} listings (may be expired)")

    h = html2text.html2text
    parts = [
        job.get("text", ""),
        h(job.get("descriptionPlain") or job.get("description") or ""),
        h(job.get("additionalPlain") or job.get("additional") or ""),
    ]
    return "\n\n".join(p for p in parts if p.strip())


def _fetch_greenhouse(url: str) -> str:
    """
    Use Greenhouse's public boards API.
    URL: https://boards.greenhouse.io/{company}/jobs/{id}
    API: https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{id}
    """
    match = re.search(r'boards\.greenhouse\.io/([^/?#]+)/jobs/(\d+)', url)
    if not match:
        raise Exception("Could not parse Greenhouse URL")
    company, job_id = match.groups()

    r = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}",
        timeout=12,
    )
    r.raise_for_status()
    data = r.json()

    h = html2text.html2text
    location = data.get("location", {}).get("name", "")
    parts = [
        data.get("title", ""),
        location,
        h(data.get("content") or ""),
    ]
    return "\n\n".join(p for p in parts if p.strip())


def _fetch_direct(url: str) -> str:
    """Scrape + extract via trafilatura (LinkedIn, Wellfound, etc.)."""
    resp = requests.get(url, headers=_HEADERS, timeout=15, allow_redirects=True)
    resp.raise_for_status()
    text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
    return text or ""


# ── Main entry point ──────────────────────────────────────────────────────────

def fetch_job_details(url: str) -> dict:
    """
    Route to the best fetcher and return a status dict.
    Returns: {'content': str, 'fetch_success': bool}
    """
    url = normalize_url(url)
    result = {"content": "", "fetch_success": False}

    try:
        if "wellfound.com" in url:
            # Explicitly mark wellfound as failure to trigger snippet fallback
            result["fetch_success"] = False
            return result

        if "lever.co" in url:
            text = _fetch_lever(url)
        elif "greenhouse.io" in url:
            text = _fetch_greenhouse(url)
        else:
            text = _fetch_direct(url)

        if len(text) >= 300:
            result["content"] = text
            result["fetch_success"] = True
        else:
            result["fetch_success"] = False
            
    except Exception:
        result["fetch_success"] = False

    return result
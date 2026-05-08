#!/usr/bin/env python3
"""
apply.py — Automated job application agent.

For each eligible job (status='New', retry_count < 3, auto_apply_ready=True):
  1. Derives the application URL from the job URL
  2. Calls Hermes to inspect the form fields on that URL
  3. Generates a tailored cover letter via the LLM
  4. Calls Hermes to fill and submit the form
  5. Marks the job as Agent Applied or Agent Failed in the DB

Run manually:
    python apply.py

Or via cron (after the scraper):
    30 4 * * * cd /root/ramlal && /root/ramlal/.venv/bin/python /root/ramlal/apply.py >> /root/ramlal/apply.log 2>&1
"""

import os
import re
import subprocess
import sys
import traceback
from datetime import datetime

# ── Fix import paths so this works both locally and from cron ─────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config.resume_parser import parse_resume
from lib.cover_letter import generate_cover_letter
from lib.db import get_eligible_jobs, mark_agent_applied, mark_agent_failed

# ── Configuration ─────────────────────────────────────────────────────────────

HERMES_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")
RESUME_PATH = os.path.join(BASE_DIR, "resume.pdf")

# Platforms we can automate — anything else is skipped
SUPPORTED_PLATFORMS = ["lever.co", "greenhouse.io", "boards.greenhouse.io"]

# Candidate profile — used for form values and cover letter generation
# Loaded once from the parsed resume at startup
CANDIDATE: dict = {}


# ── Logging ───────────────────────────────────────────────────────────────────


def log(msg: str) -> None:
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}", flush=True)


# ── Platform helpers ──────────────────────────────────────────────────────────


def is_supported(url: str) -> bool:
    """Return True if we know how to automate this job platform."""
    return any(platform in url for platform in SUPPORTED_PLATFORMS)


def get_apply_url(url: str) -> str:
    """
    Derive the application form URL from the job listing URL.
    - Lever:      jobs.lever.co/company/uuid  → jobs.lever.co/company/uuid/apply
    - Greenhouse: boards.greenhouse.io/...    → same URL (form is on the listing page)
    """
    if "lever.co" in url:
        # Strip any trailing slash then append /apply
        return url.rstrip("/") + "/apply"
    # Greenhouse and others — form is already on the listing page
    return url


# ── Hermes subprocess wrapper ─────────────────────────────────────────────────


def hermes(prompt: str, timeout: int = 120) -> str:
    """
    Run a Hermes oneshot command and return stdout as a string.
    Raises RuntimeError if the process fails or times out.
    """
    cmd = [HERMES_BIN, "-z", prompt, "-m", HERMES_MODEL]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and not output:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Hermes exited with code {result.returncode}. stderr: {stderr[:300]}"
            )
        return output
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Hermes timed out after {timeout}s")


# ── Field inspection ──────────────────────────────────────────────────────────

INSPECT_PROMPT = """Go to {url} and list every input field, text box, dropdown, radio button, and checkbox on the job application form.
List each field on its own line as a simple label, like:
- Full name
- Email
- Phone
- Resume upload
Do not add explanations. Just the field labels, one per line."""


def inspect_fields(apply_url: str) -> list[str]:
    """
    Use Hermes browser to visit the application form and return
    a list of field label strings.
    """
    prompt = INSPECT_PROMPT.format(url=apply_url)
    raw = hermes(prompt, timeout=90)

    if not raw:
        raise RuntimeError("Hermes returned empty output when inspecting form fields")

    # Parse the response — each line that looks like a field label
    fields = []
    for line in raw.splitlines():
        # Strip list markers: "- ", "1. ", "* ", etc.
        clean = re.sub(r"^[\s\-\*\d\.]+", "", line).strip()
        if clean and len(clean) > 1 and len(clean) < 120:
            fields.append(clean)

    if not fields:
        raise RuntimeError(
            f"Could not parse any fields from Hermes output:\n{raw[:300]}"
        )

    return fields


# ── Form filling ──────────────────────────────────────────────────────────────


def build_fill_prompt(apply_url: str, fields: list[str], cover_letter: str) -> str:
    """
    Build the Hermes prompt that will fill and submit the application form.
    Maps known field labels to candidate values, includes the cover letter
    for any cover letter / additional info fields.
    """
    name = CANDIDATE.get("name", "")
    email = CANDIDATE.get("email", "")
    phone = CANDIDATE.get("phone", "")
    location = CANDIDATE.get("location", "Delhi, India")
    linkedin = CANDIDATE.get("linkedin", "")
    github = CANDIDATE.get("github", "")
    portfolio = CANDIDATE.get("portfolio", "")
    current_co = CANDIDATE.get("current_company", "Freelance / Independent")
    notice = CANDIDATE.get("notice_period", "0-15 Days")
    resume_path = RESUME_PATH

    # Build a field → value mapping for the LLM to use
    field_values = []
    for field in fields:
        fl = field.lower()
        if any(k in fl for k in ["full name", "name"]):
            field_values.append(f'  "{field}": "{name}"')
        elif "email" in fl:
            field_values.append(f'  "{field}": "{email}"')
        elif "phone" in fl:
            field_values.append(f'  "{field}": "{phone}"')
        elif any(k in fl for k in ["location", "city", "address"]):
            field_values.append(f'  "{field}": "{location}"')
        elif "linkedin" in fl:
            field_values.append(f'  "{field}": "{linkedin}"')
        elif "github" in fl:
            field_values.append(f'  "{field}": "{github}"')
        elif any(k in fl for k in ["portfolio", "website", "url"]):
            field_values.append(f'  "{field}": "{portfolio}"')
        elif any(k in fl for k in ["current company", "company"]):
            field_values.append(f'  "{field}": "{current_co}"')
        elif any(k in fl for k in ["notice", "notice period"]):
            field_values.append(f'  "{field}": "{notice}"')
        elif any(k in fl for k in ["resume", "cv", "upload"]):
            field_values.append(f'  "{field}": upload file at "{resume_path}"')
        elif any(k in fl for k in ["cover letter", "additional", "message", "why"]):
            # Paste cover letter — truncated to avoid prompt length issues
            field_values.append(f'  "{field}": (paste the cover letter below)')
        elif any(
            k in fl for k in ["years", "experience", "ctc", "salary", "compensation"]
        ):
            field_values.append(f'  "{field}": leave blank or skip if optional')
        elif any(k in fl for k in ["twitter", "other"]):
            field_values.append(f'  "{field}": leave blank')
        else:
            field_values.append(
                f'  "{field}": leave blank if optional, otherwise use best judgment'
            )

    values_block = "\n".join(field_values)

    return f"""Go to {apply_url} and fill out the job application form using the values below. Then submit the form.

FIELD VALUES:
{values_block}

COVER LETTER (paste into any cover letter, additional information, or message field):
---
{cover_letter}
---

IMPORTANT INSTRUCTIONS:
- Fill every required field. Skip optional fields that are blank above.
- For the resume upload, upload the file at: {resume_path}
- For radio buttons (e.g. Notice Period), select the option that matches the value given.
- Check any consent/contact checkboxes if present.
- After filling all fields, click the Submit button.
- If a CAPTCHA appears, stop and report "CAPTCHA_BLOCKED".
- If you are redirected to a confirmation or thank-you page, report "SUCCESS".
- If the form fails to submit for any reason, report "FAILED: <reason>".
- Reply with one of: SUCCESS, CAPTCHA_BLOCKED, or FAILED: <reason>"""


def fill_and_submit(apply_url: str, fields: list[str], cover_letter: str) -> str:
    """
    Use Hermes to fill and submit the application form.
    Returns the outcome string from Hermes: SUCCESS, CAPTCHA_BLOCKED, or FAILED: ...
    """
    prompt = build_fill_prompt(apply_url, fields, cover_letter)
    raw = hermes(prompt, timeout=180)  # form filling takes longer

    if not raw:
        return "FAILED: Hermes returned empty output during form fill"

    # Look for our sentinel words anywhere in the response
    upper = raw.upper()
    if "SUCCESS" in upper:
        return "SUCCESS"
    if "CAPTCHA" in upper or "CAPTCHA_BLOCKED" in upper:
        return "CAPTCHA_BLOCKED"
    if "FAILED" in upper:
        # Extract the reason after "FAILED:"
        match = re.search(r"FAILED[:\s]+(.+)", raw, re.IGNORECASE)
        reason = match.group(1).strip()[:300] if match else raw[:300]
        return f"FAILED: {reason}"

    # Hermes didn't use our sentinels — treat as failure with raw output
    return f"FAILED: Unexpected response — {raw[:200]}"


# ── Per-job apply logic ───────────────────────────────────────────────────────


def apply_to_job(job: dict) -> None:
    job_id = job["id"]
    url = job["url"]
    title = job["title"]
    company = job["company"]
    label = f"{title} @ {company} (id={job_id})"

    log(f"  Starting: {label}")

    # Step 1 — check platform support
    if not is_supported(url):
        raise RuntimeError(
            f"Unsupported platform — cannot automate {url}. "
            f"Only Lever and Greenhouse are supported."
        )

    apply_url = get_apply_url(url)
    log(f"  Apply URL: {apply_url}")

    # Step 2 — inspect form fields
    log("  Inspecting form fields...")
    fields = inspect_fields(apply_url)
    log(f"  Found {len(fields)} fields: {fields}")

    # Step 3 — generate cover letter
    log("  Generating cover letter...")
    cover_letter = generate_cover_letter(job, CANDIDATE)
    log(f"  Cover letter generated ({len(cover_letter.split())} words)")

    # Step 4 — fill and submit
    log("  Filling and submitting form...")
    outcome = fill_and_submit(apply_url, fields, cover_letter)
    log(f"  Outcome: {outcome}")

    # Step 5 — update DB based on outcome
    if outcome == "SUCCESS":
        mark_agent_applied(job_id)
        log(f"  ✓ Marked as Agent Applied")
    elif outcome == "CAPTCHA_BLOCKED":
        mark_agent_failed(job_id, "CAPTCHA encountered — human intervention required")
        log(f"  ✗ Marked as Agent Failed (CAPTCHA)")
    else:
        mark_agent_failed(job_id, outcome)
        log(f"  ✗ Marked as Agent Failed: {outcome}")


# ── Main ──────────────────────────────────────────────────────────────────────


def run() -> None:
    start = datetime.utcnow()
    log("=" * 60)
    log("Ramlal apply agent started")
    log("=" * 60)

    # Load resume data once — used for cover letter generation and candidate info
    if not os.path.exists(RESUME_PATH):
        log(f"FATAL: Resume not found at {RESUME_PATH}")
        sys.exit(1)

    log("Parsing resume...")
    resume_data = parse_resume(RESUME_PATH)
    CANDIDATE.update(resume_data)

    # Supplement with fields resume_parser doesn't extract
    # Set these in your .env or directly here
    CANDIDATE.setdefault("email", os.getenv("CANDIDATE_EMAIL", ""))
    CANDIDATE.setdefault("phone", os.getenv("CANDIDATE_PHONE", ""))
    CANDIDATE.setdefault("linkedin", os.getenv("CANDIDATE_LINKEDIN", ""))
    CANDIDATE.setdefault("github", os.getenv("CANDIDATE_GITHUB", ""))
    CANDIDATE.setdefault("portfolio", os.getenv("CANDIDATE_PORTFOLIO", ""))
    CANDIDATE.setdefault(
        "current_company",
        os.getenv("CANDIDATE_CURRENT_COMPANY", "Freelance / Independent"),
    )
    CANDIDATE.setdefault(
        "notice_period", os.getenv("CANDIDATE_NOTICE_PERIOD", "0-15 Days")
    )

    log(
        f"Candidate: {CANDIDATE.get('name')} | {CANDIDATE.get('experience_level')} | {CANDIDATE.get('location')}"
    )

    # Fetch eligible jobs — only auto_apply_ready ones
    all_eligible = get_eligible_jobs()
    jobs = [j for j in all_eligible if j.get("auto_apply_ready")]

    log(
        f"Found {len(all_eligible)} eligible jobs total, {len(jobs)} with auto_apply_ready=True"
    )

    if not jobs:
        log("Nothing to apply to. Exiting.")
        _print_summary(start, 0, 0, 0)
        return

    applied = 0
    failed = 0
    skipped = 0

    for i, job in enumerate(jobs, 1):
        log(f"\n[{i}/{len(jobs)}] {job['title']} @ {job['company']}")
        try:
            apply_to_job(job)
            applied += 1
        except Exception as e:
            reason = str(e)[:400]
            log(f"  ERROR: {reason}")
            traceback.print_exc()
            try:
                mark_agent_failed(job["id"], reason)
            except Exception as db_err:
                log(f"  Also failed to update DB: {db_err}")
            failed += 1

    _print_summary(start, len(jobs), applied, failed)


def _print_summary(start: datetime, total: int, applied: int, failed: int) -> None:
    elapsed = (datetime.utcnow() - start).seconds
    mins, secs = divmod(elapsed, 60)
    log("\n" + "=" * 60)
    log(f"Apply run complete in {mins}m {secs}s")
    log(f"  Jobs attempted:  {total}")
    log(f"  Agent Applied:   {applied}")
    log(f"  Agent Failed:    {failed}")
    log("=" * 60)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)

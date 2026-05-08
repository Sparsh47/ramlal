import json
import re

from config.groq_client import ask_hermes


def _extract_json_object(text: str) -> dict:
    """
    Robustly extract a JSON object from LLM output even if it's wrapped
    in markdown code fences or has leading/trailing prose.
    """
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find the first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON object found in LLM response: {text[:200]}")


def score_job(job: dict, resume_data: dict, retries: int = 3) -> dict:
    system_prompt = """You are a job fit evaluator. Return ONLY a valid JSON object, no markdown, no extra text."""

    user_prompt = f"""Score this job listing against the candidate's profile.

Return this exact JSON:
{{
  "score": <1-10>,
  "title": "<job title extracted from listing>",
  "company": "<company name if visible>",
  "reasons": "<one line why it's a good or bad fit>"
}}

Candidate skills: {", ".join(resume_data["skills"]["languages"] + resume_data["skills"]["frameworks"][:5])}
Experience level: {resume_data["experience_level"]}
Location: {resume_data["location"]}

Job listing:
Title: {job["title"]}
URL: {job["url"]}
Snippet: {job["snippet"]}
"""

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = ask_hermes(user_prompt, system=system_prompt)
            result = _extract_json_object(response)

            # Validate required fields and types
            score = result.get("score")
            if not isinstance(score, (int, float)) or not (1 <= score <= 10):
                raise ValueError(f"Invalid score value: {score!r}")

            # Merge LLM result into the original job dict
            scored_job = job.copy()
            scored_job.update(result)
            return scored_job
        except Exception as e:
            last_error = e
            print(
                f"[job_scorer] Attempt {attempt}/{retries} failed for {job.get('url', '?')}: {e}"
            )

    raise RuntimeError(f"Failed to score job after {retries} attempts: {last_error}")


def score_all_jobs(jobs: list[dict], resume_data: dict) -> list[dict]:
    scored = []
    for job in jobs:
        try:
            scored.append(score_job(job, resume_data))
        except Exception as e:
            print(f"[job_scorer] Permanently skipping {job.get('url', '?')}: {e}")
    return sorted(scored, key=lambda x: x.get("score", 0), reverse=True)

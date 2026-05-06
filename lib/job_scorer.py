import json
from config.groq_client import ask_hermes

def score_job(job: dict, resume_data: dict) -> dict:
    system_prompt = """You are a job fit evaluator. Return ONLY a valid JSON object, no markdown, no extra text."""

    user_prompt = f"""Score this job listing against the candidate's profile.

Return this exact JSON:
{{
  "score": <1-10>,
  "title": "<job title extracted from listing>",
  "company": "<company name if visible>",
  "reasons": "<one line why it's a good or bad fit>"
}}

Candidate skills: {', '.join(resume_data['skills']['languages'] + resume_data['skills']['frameworks'][:5])}
Experience level: {resume_data['experience_level']}
Location: {resume_data['location']}

Job listing:
Title: {job['title']}
URL: {job['url']}
Snippet: {job['snippet']}
"""

    response = ask_hermes(user_prompt, system=system_prompt)
    result = json.loads(response)
    
    # Merge the LLM scoring results into the original job dict to preserve 'snippet' and other original data
    scored_job = job.copy()
    scored_job.update(result)
    return scored_job


def score_all_jobs(jobs: list[dict], resume_data: dict) -> list[dict]:
    scored = []
    for job in jobs:
        try:
            scored.append(score_job(job, resume_data))
        except Exception as e:
            print(f"Skipping {job['url']}: {e}")
    return sorted(scored, key=lambda x: x['score'], reverse=True)
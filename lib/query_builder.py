import json
import re

from config.groq_client import ask_hermes


def _extract_json_array(text: str) -> list:
    """
    Robustly extract a JSON array from LLM output even if it's wrapped
    in markdown code fences or has leading/trailing prose.
    """
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find the first [...] block
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON array found in LLM response: {text[:200]}")


def build_search_queries(resume_data: dict, retries: int = 3) -> list[str]:
    system_prompt = """You are a job search expert. Generate targeted job search queries based on a candidate's profile. Return ONLY a valid JSON array of strings. No markdown, no explanation, just raw JSON array."""

    user_prompt = f"""Generate 12 job search queries to find software job listings. Each query will be passed directly to a search engine like Google.

Generate TWO types of queries:

TYPE A — 7 queries with a standard job title + 1-2 key skills (catches normal postings):
- Include a standard role like "Software Engineer", "Frontend Developer", "Full Stack Developer", "AI Engineer", "Mobile Developer"
- Add 1-2 core skills and optionally one location ("Remote", "India", "Delhi")
- Example: "Frontend Developer React Remote", "Full Stack Engineer Node.js India"

TYPE B — 5 queries with ONLY skills, NO job title (catches non-generic roles like "Product Engineer", "Founding Engineer", "Software Craftsman", "Growth Engineer"):
- Use 2-3 popular, broadly-searched skills that naturally appear together in job postings
- Optionally add a location word
- Use POPULAR skills only — do NOT use very niche tools (no "Qdrant", no "Ollama", no "Trafilatura")
- Example: "React TypeScript Remote", "Node.js PostgreSQL India", "Python LangChain Remote"

Rules for ALL queries:
- NO platform/brand names (no "LinkedIn", "Naukri", "GitHub", "Wellfound")
- NO punctuation, NO quotes inside queries
- Keep each query under 6 words
- Cover frontend, backend, AI/LLM, and mobile skill areas

Candidate's skill clusters:
- Frontend: {", ".join(resume_data["skills"]["frameworks"][:4])}
- Backend/DB: {", ".join(resume_data["skills"]["languages"][:3])}, {", ".join(resume_data["skills"]["frameworks"][4:7])}
- AI/LLM: {", ".join(resume_data["skills"]["ai_ml"][:4])}
- Mobile: React Native, Expo, TypeScript

Return format: ["query1", "query2", ...]"""

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = ask_hermes(user_prompt, system_prompt)
            queries = _extract_json_array(response)
            if not isinstance(queries, list) or not queries:
                raise ValueError("LLM returned empty or non-list response")
            return [str(q) for q in queries]
        except Exception as e:
            last_error = e
            print(f"[query_builder] Attempt {attempt}/{retries} failed: {e}")

    raise RuntimeError(
        f"Failed to build search queries after {retries} attempts: {last_error}"
    )

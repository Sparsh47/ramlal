import json
import re

import fitz

from .groq_client import ask_hermes


def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()


def _extract_json_object(text: str) -> dict:
    """
    Robustly extract a JSON object from LLM output even if it's wrapped
    in markdown code fences or has leading/trailing prose.
    """
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON object found in LLM response: {text[:200]}")


def parse_resume(pdf_path: str, retries: int = 3) -> dict:
    text = extract_text_from_pdf(pdf_path)

    system_prompt = """You are a resume parser. Extract structured data from the resume text and return ONLY a valid JSON object with no extra text, no markdown, no code blocks. Just raw JSON."""

    user_prompt = f"""Extract the following from this resume and return as JSON:
{{
  "name": "",
  "email": "",
  "location": "",
  "job_titles": [],
  "skills": {{
    "languages": [],
    "frameworks": [],
    "ai_ml": [],
    "infrastructure": [],
    "concepts": []
  }},
  "years_experience": 0,
  "experience_level": "",
  "industries": [],
  "current_role": "",
  "education": ""
}}

Resume:
{text}"""

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = ask_hermes(user_prompt, system_prompt)
            result = _extract_json_object(response)
            # Ensure skills sub-keys exist so downstream code never KeyErrors
            result.setdefault("skills", {})
            for key in (
                "languages",
                "frameworks",
                "ai_ml",
                "infrastructure",
                "concepts",
            ):
                result["skills"].setdefault(key, [])
            result.setdefault("location", "")
            result.setdefault("experience_level", "")
            return result
        except Exception as e:
            last_error = e
            print(f"[resume_parser] Attempt {attempt}/{retries} failed: {e}")

    raise RuntimeError(f"Failed to parse resume after {retries} attempts: {last_error}")


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "resume.pdf"
    data = parse_resume(path)
    print(json.dumps(data, indent=2))

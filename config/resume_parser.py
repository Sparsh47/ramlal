import fitz
import json
from .groq_client import ask_hermes

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""

    for page in doc:
        text+=page.get_text()
    return text.strip()

def parse_resume(pdf_path: str):
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

    response = ask_hermes(user_prompt, system_prompt)

    return json.loads(response)

if __name__ == "__main__":
    data = parse_resume("resume.pdf")
    print(json.dumps(data, indent=2))
"""
lib/cover_letter.py

Generates a tailored, human-sounding cover letter for a job posting using
the Groq-backed LLM (llama-3.3-70b-versatile via ask_hermes).

Usage:
    from lib.cover_letter import generate_cover_letter
    letter = generate_cover_letter(job, resume_data)
"""

from config.groq_client import ask_hermes

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BANNED_PHRASES = [
    "i am writing to apply",
    "i believe i would be a great fit",
    "i am excited to",
    "i am passionate about",
    "leverage my skills",
    "i would love to",
    "please find attached",
    "thank you for your consideration",
    "make a meaningful contribution",
    "make meaningful contributions",
    "strong candidate",
    "hit the ground running",
    "looking forward to discussing",
    "seems like a natural fit",
    "i think my",
    "i'm confident that",
    "i am confident that",
    "aligns with my",
    "resonates with me",
    "i'm drawn to",
    "i am drawn to",
    "i'm confident in my ability",
    "i am confident in my ability",
    "makes me a strong fit",
    "makes me a good fit",
    "makes me a great fit",
    "i was drawn to",
    "particularly interesting to me",
    "suggests that they value",
    "am interested in discussing",
    "caught my attention",
    "caught my eye",
    "stands out to me",
    "seems like a good opportunity",
    "real-world setting",
    "i've built multiple projects",
    "i have built multiple projects",
    "i've worked on multiple",
    "i've spent a significant amount of time",
    "i have spent a significant amount of time",
    "i'm ready to contribute",
    "i am ready to contribute",
    "am ready to discuss",
    "i'm open to discussing",
]

SYSTEM_PROMPT = (
    "You are a professional cover letter writer. You write concise, human, specific cover letters. "
    "You never use filler phrases. You never use bullet points. You write exactly 3 plain paragraphs. "
    "Return only the cover letter text — no subject line, no metadata, nothing else. "
    "You are physically incapable of writing these words or phrases: 'excited', 'passionate', "
    "'confident', 'drawn to', 'aligns with', 'resonates', 'strong fit', 'great fit', "
    "'meaningful contribution', 'strong candidate', 'looking forward', 'leverage'. "
    "If you are about to write any of these words, stop and rewrite that sentence entirely."
)

MAX_ATTEMPTS = 5
MIN_LENGTH = 100


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate(text: str) -> tuple[bool, str]:
    """
    Returns (True, "") if the cover letter passes all checks.
    Returns (False, reason) if it fails.
    """
    if len(text) < MIN_LENGTH:
        return (
            False,
            f"Response too short ({len(text)} chars, need at least {MIN_LENGTH})",
        )

    lower = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            return False, f'Contains banned phrase: "{phrase}"'

    return True, ""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def _build_prompt(job: dict, resume_data: dict, retry_note: str = "") -> str:
    title = job.get("title", "")
    company = job.get("company", "")

    # Use the longer of reasons / snippet as the JD context
    reasons = job.get("reasons", "") or ""
    snippet = job.get("snippet", "") or ""
    jd_content = reasons if len(reasons) >= len(snippet) else snippet

    name = resume_data.get("name", "")
    first_name = name.split()[0] if name else ""
    experience_level = resume_data.get("experience_level", "")
    current_role = resume_data.get("current_role", "")
    location = resume_data.get("location", "")

    skills_data = resume_data.get("skills", {})
    languages = skills_data.get("languages", [])[:4]
    frameworks = skills_data.get("frameworks", [])[:4]
    ai_ml = skills_data.get("ai_ml", [])[:2]
    top_skills = languages + frameworks + ai_ml

    skills_str = ", ".join(top_skills) if top_skills else "various technologies"

    retry_line = (
        f"\n\nPrevious attempt was rejected. Do not use filler phrases."
        if retry_note
        else ""
    )

    # Pull structured resume sections for the prompt
    projects = resume_data.get("projects", [])
    experience = resume_data.get("experience", [])
    ai_ml_full = skills_data.get("ai_ml", [])

    # Format projects block — name + one-line outcome each
    projects_block = ""
    if projects:
        lines = []
        for p in projects:
            name_p = p.get("name", "")
            outcome = p.get("outcome", p.get("description", ""))
            tech = ", ".join(p.get("tech", []))
            line = f"- {name_p}"
            if outcome:
                line += f": {outcome}"
            if tech:
                line += f" (tech: {tech})"
            lines.append(line)
        projects_block = "\n".join(lines)

    # Format experience block
    experience_block = ""
    if experience:
        lines = []
        for e in experience:
            role = e.get("role", "")
            company = e.get("company", "")
            bullets = e.get("bullets", [])
            lines.append(f"- {role} @ {company}")
            for b in bullets[:2]:  # top 2 bullets per role
                lines.append(f"    • {b}")
        experience_block = "\n".join(lines)

    ai_ml_str = ", ".join(ai_ml_full) if ai_ml_full else ""

    prompt = f"""Write a cover letter for the following job. This will be sent to a real recruiter — every sentence must be specific and grounded in the candidate's actual work.

---
JOB DETAILS
Title: {title}
Company: {company}
Job Description:
{jd_content if jd_content else "(no description available — use the title and company to infer context)"}

---
CANDIDATE
Name: {name}
Current Role: {current_role}
Experience: {experience_level}
Location: {location}
Core Skills: {skills_str}
AI/LLM Experience: {ai_ml_str if ai_ml_str else "none listed"}

Real Projects (use these — do NOT invent projects):
{projects_block if projects_block else "(no projects listed — infer from skills and role)"}

Work Experience:
{experience_block if experience_block else "(no experience listed — infer from current role)"}

---
STRICT INSTRUCTIONS — follow every one of these exactly:

1. First line must be exactly: "Hiring Team," — nothing else on that line.
2. Blank line after "Hiring Team,", then exactly 3 paragraphs of plain prose. No bullet points.
3. Paragraph 1 (2-3 sentences): Open with something specific about THIS company or THIS role — not the tech stack. What problem are they solving? What product area? What does the JD reveal about how the team works? One concrete observation about the company, then one sentence connecting your background to it.
4. Paragraph 2 (3-4 sentences): Pick 2-3 skills that directly match the JD requirements. For each one, name a SPECIFIC project from the candidate's project list above and say what it did or what outcome it achieved. Format: "I built [project name] using [skill], which [concrete outcome]." Do NOT say "I've built multiple projects" — name the actual project. If the JD mentions AI/LLM work and the candidate has AI/LLM experience, mention it explicitly here.
5. Paragraph 3 (2-3 sentences): Closing. Mention based in {location}, open to remote, available immediately. One sentence of genuine interest — not a filler phrase. Do NOT say "looking forward to" anything.
6. Last line: sign off with only "{first_name}" — nothing else after it.
7. Total word count: 200-280 words. Not shorter, not longer.
8. NEVER use any of these phrases (treat this as a hard filter — rewrite any sentence containing them):
   - "caught my attention" / "caught my eye" / "stands out to me"
   - "I am writing to apply" / "I believe I would be a great fit"
   - "I am excited to" / "I am passionate about" / "leverage my skills"
   - "make a meaningful contribution" / "strong candidate" / "hit the ground running"
   - "looking forward to discussing" / "thank you for your consideration"
   - "aligns with my" / "resonates with me" / "I'm confident that"
   - "seems like a good opportunity" / "real-world setting"
   - "I've built multiple projects" / "I've spent a significant amount of time"
9. Write the way a senior developer actually writes — direct, specific, zero fluff.
10. Do NOT add a subject line, date, address block, or any metadata. Just the letter starting with "Hiring Team,".{retry_line}"""

    return prompt


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_cover_letter(job: dict, resume_data: dict) -> str:
    """
    Generate a tailored cover letter for the given job and candidate resume.

    Args:
        job:         A job dict as returned by get_eligible_jobs(). Expected keys:
                     title, company, reasons, snippet (optional).
        resume_data: A dict with candidate info. Expected keys:
                     name, current_role, experience_level, location,
                     skills (dict with languages, frameworks, ai_ml).

    Returns:
        A plain cover letter string (no JSON, no wrapping).

    Raises:
        RuntimeError: If all 3 attempts produce an invalid cover letter.
    """
    last_failure_reason = "Unknown"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        retry_note = attempt > 1  # add the "previous attempt rejected" note on retries
        prompt = _build_prompt(job, resume_data, retry_note=retry_note)

        raw = ask_hermes(prompt, system=SYSTEM_PROMPT)
        cover_letter = raw.strip()

        passed, reason = _validate(cover_letter)
        if passed:
            return cover_letter

        last_failure_reason = reason
        print(
            f"[cover_letter] Attempt {attempt}/{MAX_ATTEMPTS} failed validation: {reason}"
        )

    raise RuntimeError(
        f"generate_cover_letter failed after {MAX_ATTEMPTS} attempts. "
        f"Last failure reason: {last_failure_reason}\n"
        f"Job: {job.get('title')} @ {job.get('company')}"
    )

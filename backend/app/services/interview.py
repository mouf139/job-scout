import json

import anthropic

from app.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

EXTRACTION_SYSTEM = """You are a resume analysis assistant. Extract structured information from the resume text provided.
Return a JSON object with exactly these fields:
{
  "name": "Full name",
  "education": "Degree, school, graduation year/status",
  "skills": "Comma-separated list of skills",
  "work_history": "Brief summary of work experience with titles and companies",
  "industries": "Industries worked in, comma-separated",
  "certifications": "Certifications if any, or null",
  "past_job_titles": ["list", "of", "job", "titles"],
  "summary": "2-3 sentence professional summary"
}
Return ONLY valid JSON, no markdown fences or explanation."""

INTERVIEW_SYSTEM = """You are a quick, friendly career coach onboarding a user for Job Scout.

You have the user's resume data. Don't re-ask what it already answers.

Topics to cover (skip what the resume answers):
1. Confirm resume — anything wrong or outdated?
2. Career direction — same field, change, step up?
3. Role type — full-time, part-time, internship, contract?
4. Target titles — what titles to search?
5. Location & commute
6. Remote preference
7. Salary range
8. Target industries
9. Deal-breakers — what to avoid
10. Anything else?

FORMATTING RULES (follow exactly):
- Keep every response UNDER 20 words total
- Put the question in **bold** using markdown
- One short context sentence max, then the bold question
- No bullet lists, no long intros, no pleasantries
- ONE question per message

Example good responses:
"Got it, finance background noted. **What job titles are you targeting?**"
"Makes sense. **Remote, hybrid, or on-site?**"
"Your resume looks solid. **Anything outdated or missing?**"

INTERVIEW FLOW:
- 5-7 questions max. Skip what the resume covers.
- When done, give a 1-2 sentence summary and add [INTERVIEW_COMPLETE] at the very end."""

CRITERIA_SYSTEM = """You are generating job search criteria based on a user's resume and interview answers.
Return a JSON object with exactly these fields:
{
  "titles": ["list of 3-5 target job titles"],
  "include_keywords": ["relevant skills and keywords to search for"],
  "exclude_keywords": ["terms to avoid in job listings"],
  "location": "city, state or region",
  "radius_miles": 25,
  "remote_preference": "remote|hybrid|on_site|any",
  "experience_level": "entry|mid|senior|executive",
  "job_type": "full_time|part_time|internship|contract",
  "salary_minimum": null or integer,
  "industries": ["list of target industries"]
}
Return ONLY valid JSON, no markdown fences or explanation."""


def _parse_json_response(text: str) -> dict:
    import re
    cleaned = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', cleaned)
    if match:
        cleaned = match.group(1).strip()
    return json.loads(cleaned)


async def extract_resume(resume_text: str) -> dict:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": f"Extract information from this resume:\n\n{resume_text}"}],
    )
    return _parse_json_response(message.content[0].text)


async def chat_interview(messages: list, resume_extraction: dict) -> dict:
    resume_context = json.dumps(resume_extraction, indent=2)

    system = f"{INTERVIEW_SYSTEM}\n\nResume extraction data:\n{resume_context}"

    api_messages = []
    for msg in messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=system,
        messages=api_messages,
    )

    reply = response.content[0].text
    is_complete = "[INTERVIEW_COMPLETE]" in reply
    clean_reply = reply.replace("[INTERVIEW_COMPLETE]", "").strip()

    return {
        "reply": clean_reply,
        "is_complete": is_complete,
    }


async def generate_criteria(resume_extraction: dict, interview_messages: list) -> dict:
    conversation_summary = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in interview_messages
    )

    prompt = f"""Based on this resume data and interview conversation, generate job search criteria.

Resume data:
{json.dumps(resume_extraction, indent=2)}

Interview conversation:
{conversation_summary}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=CRITERIA_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json_response(message.content[0].text)

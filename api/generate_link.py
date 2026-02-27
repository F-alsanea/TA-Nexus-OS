"""
╔══════════════════════════════════════════════════════════════╗
║  GENERATE LINK — Dynamic Screener UUID Generator            ║
║  Worker C: Creates unique assessment link per candidate     ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import uuid
import json
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
APP_URL = os.getenv("APP_URL", "http://localhost:8000")


class ScreeningSession(BaseModel):
    session_id: str
    candidate_id: str
    job_id: str
    screening_url: str
    questions: list[dict]
    question_count: int
    created_at: str


async def generate_tailored_questions(
    candidate_data: dict,
    job_description: str,
    skill_gaps: list[str] = None
) -> list[dict]:
    """
    Worker C: Generate 5-7 sniper questions tailored to THIS candidate's gaps.
    Different for each candidate — no repeated questions across different profiles.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    gap_context = f"Key skill gaps to probe: {skill_gaps}" if skill_gaps else "Probe for general competency."

    prompt = f"""
You are Worker C — Intelligence Analyst for TA Nexus.

Generate 6 highly targeted screening questions for this specific candidate.
These questions must NOT be generic — they must target this candidate's specific gaps and experience.

Candidate Profile:
{json.dumps(candidate_data, indent=2, default=str)[:3000]}

Job Requirements:
{job_description[:2000]}

{gap_context}

Rules:
1. Mix: 3 technical + 2 behavioral + 1 situational
2. Include at least 2 "trap" questions for weak areas
3. Each question must be answerable in 3-5 sentences
4. Avoid yes/no questions
5. Make questions progressively harder

Respond with this JSON array:
[
  {{
    "id": 1,
    "type": "technical/behavioral/situational",
    "question": "...",
    "ideal_keywords": ["keyword1", "keyword2"],
    "trap_for": "skill gap or weakness this targets",
    "difficulty": "easy/medium/hard"
  }}
]

Only output valid JSON array. No extra text.
"""

    response = model.generate_content(prompt)
    questions = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    return questions


async def create_screening_session(
    candidate_id: str,
    job_id: str,
    candidate_data: dict = None,
    job_description: str = "",
    skill_gaps: list[str] = None
) -> dict:
    """
    Creates a unique screening session with tailored questions.
    Stores in Supabase and returns the screening URL.
    """
    from database.supabase_handler import SupabaseHandler
    from datetime import datetime, timezone

    db = SupabaseHandler()

    # Generate tailored questions
    questions = await generate_tailored_questions(
        candidate_data or {"candidate_id": candidate_id},
        job_description,
        skill_gaps
    )

    session_id = str(uuid.uuid4())
    screening_url = f"{APP_URL}/screen/{session_id}"
    created_at = datetime.now(timezone.utc).isoformat()

    session = ScreeningSession(
        session_id=session_id,
        candidate_id=candidate_id,
        job_id=job_id,
        screening_url=screening_url,
        questions=questions,
        question_count=len(questions),
        created_at=created_at
    )

    # Save to Supabase
    await db.save_screening_session(session.model_dump())

    return {
        "session_id": session_id,
        "screening_url": screening_url,
        "question_count": len(questions),
        "message": f"Screening link generated for candidate {candidate_id}",
        "expires_in": "7 days"
    }

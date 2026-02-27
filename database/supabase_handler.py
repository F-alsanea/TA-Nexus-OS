"""
TA Nexus — Supabase Database Handler
=====================================
Manages all persistence: candidates, screening sessions, scores, reminders.
Project: https://jvsdazoxmcehnazxthwm.supabase.co
"""

import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  Client Singleton
# ─────────────────────────────────────────────

_client: Optional[Client] = None


def get_client() -> Client:
    """Return (or create) the singleton Supabase client."""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY must be set.")
        _client = create_client(url, key)
    return _client


# ─────────────────────────────────────────────
#  CANDIDATES
# ─────────────────────────────────────────────

def save_candidate(candidate_id: str, candidate_data: dict) -> dict:
    """Alias for upsert_candidate to support the API upload_cv route."""
    candidate_data["id"] = candidate_id
    return upsert_candidate(candidate_data)

def upsert_candidate(candidate_data: dict) -> dict:
    """
    Insert or update a candidate record.
    candidate_data keys: name, email, phone, current_title, current_company,
                         skills (list), cv_text, source_job_id, overall_score,
                         retention_risk, salary_risk, cultural_risk, domain_color
    Returns the saved record.
    """
    client = get_client()
    payload = {
        "id": candidate_data.get("id", str(uuid.uuid4())),
        "name": candidate_data.get("name", ""),
        "email": candidate_data.get("email", ""),
        "phone": candidate_data.get("phone", ""),
        "current_title": candidate_data.get("current_title", ""),
        "current_company": candidate_data.get("current_company", ""),
        "skills": candidate_data.get("skills", []),
        "cv_text": candidate_data.get("cv_text", ""),
        "source_job_id": candidate_data.get("source_job_id"),
        "overall_score": candidate_data.get("overall_score"),
        "retention_risk": candidate_data.get("retention_risk"),
        "salary_risk": candidate_data.get("salary_risk"),
        "cultural_risk": candidate_data.get("cultural_risk"),
        "domain_color": candidate_data.get("domain_color", "green"),
        "email_verified": candidate_data.get("email_verified", False),
        "updated_at": datetime.utcnow().isoformat(),
    }
    result = client.table("candidates").upsert(payload).execute()
    logger.info(f"[DB] Upserted candidate: {payload['name']} ({payload['id']})")
    return result.data[0] if result.data else payload


def get_candidate(candidate_id: str) -> Optional[dict]:
    """Fetch a single candidate by ID."""
    client = get_client()
    result = client.table("candidates").select("*").eq("id", candidate_id).single().execute()
    return result.data


def list_candidates(job_id: Optional[str] = None, limit: int = 50) -> list:
    """List candidates, optionally filtered by job_id."""
    client = get_client()
    query = client.table("candidates").select("*").order("overall_score", desc=True).limit(limit)
    if job_id:
        query = query.eq("source_job_id", job_id)
    result = query.execute()
    return result.data or []


def get_all_candidates_with_scores() -> list:
    """Get all candidates for the dashboard."""
    return list_candidates()


def delete_candidate(candidate_id: str) -> bool:
    """Hard-delete a candidate."""
    client = get_client()
    client.table("candidates").delete().eq("id", candidate_id).execute()
    logger.info(f"[DB] Deleted candidate: {candidate_id}")
    return True


# ─────────────────────────────────────────────
#  SCREENING SESSIONS
# ─────────────────────────────────────────────

def create_screening_session(candidate_id: str, job_id: str, questions: list) -> dict:
    """
    Create a UUID-based screening session with tailored questions.
    Returns the session record including the unique screening URL slug.
    """
    client = get_client()
    session_uuid = str(uuid.uuid4())
    payload = {
        "id": session_uuid,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "questions": questions,           # list of {"id", "text", "type", "ideal_answer"}
        "status": "pending",              # pending | in_progress | completed
        "screening_url": f"/screen/{session_uuid}",
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
    }
    result = client.table("screening_sessions").insert(payload).execute()
    logger.info(f"[DB] Created screening session: {session_uuid} for candidate {candidate_id}")
    return result.data[0] if result.data else payload


def get_screening_session(session_id: str) -> Optional[dict]:
    """Fetch a screening session by its UUID."""
    client = get_client()
    result = client.table("screening_sessions").select("*").eq("id", session_id).single().execute()
    return result.data


def submit_screening_answers(session_id: str, answers: list) -> dict:
    """
    Store candidate answers and mark the session as completed.
    answers: list of {"question_id", "answer_text"}
    """
    client = get_client()
    result = client.table("screening_sessions").update({
        "answers": answers,
        "status": "completed",
        "submitted_at": datetime.utcnow().isoformat(),
    }).eq("id", session_id).execute()
    logger.info(f"[DB] Answers submitted for session: {session_id}")
    return result.data[0] if result.data else {}


def list_sessions_for_candidate(candidate_id: str) -> list:
    """Get all screening sessions for a candidate."""
    client = get_client()
    result = (
        client.table("screening_sessions")
        .select("*")
        .eq("candidate_id", candidate_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────────
#  SCORES
# ─────────────────────────────────────────────

def save_score(session_id: str, candidate_id: str, score_data: dict) -> dict:
    """
    Persist the final computed score after Evaluator-Optimizer pass.
    score_data keys: total_score, accuracy_score, depth_score, cultural_score,
                     skill_gap (list), risk_flags (dict), interview_guide_url
    """
    client = get_client()
    payload = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "candidate_id": candidate_id,
        "total_score": score_data.get("total_score", 0),
        "accuracy_score": score_data.get("accuracy_score", 0),
        "depth_score": score_data.get("depth_score", 0),
        "cultural_score": score_data.get("cultural_score", 0),
        "skill_gap": score_data.get("skill_gap", []),
        "risk_flags": score_data.get("risk_flags", {}),
        "interview_guide_url": score_data.get("interview_guide_url"),
        "scored_at": datetime.utcnow().isoformat(),
    }
    result = client.table("scores").insert(payload).execute()
    logger.info(f"[DB] Score saved: {score_data.get('total_score')}/100 for candidate {candidate_id}")
    return result.data[0] if result.data else payload


def get_scores_for_job(job_id: str) -> list:
    """Get all scored candidates for a job (for comparison dashboard)."""
    client = get_client()
    result = (
        client.table("scores")
        .select("*, candidates(name, email, current_title), screening_sessions(job_id)")
        .eq("screening_sessions.job_id", job_id)
        .order("total_score", desc=True)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────────
#  REMINDERS (Auto-Scheduler)
# ─────────────────────────────────────────────

def schedule_reminder(candidate_id: str, score: float, recruiter_note: str = "") -> Optional[dict]:
    """
    Auto-schedule a follow-up for high-score candidates (score > 85).
    Returns the reminder record or None if score is too low.
    """
    if score < 85:
        logger.info(f"[DB] No reminder scheduled for candidate {candidate_id} (score={score})")
        return None

    client = get_client()
    follow_up_date = datetime.utcnow() + timedelta(days=3)
    payload = {
        "id": str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "follow_up_date": follow_up_date.isoformat(),
        "status": "pending",           # pending | sent | dismissed
        "recruiter_note": recruiter_note,
        "trigger_score": score,
        "created_at": datetime.utcnow().isoformat(),
    }
    result = client.table("reminders").insert(payload).execute()
    logger.info(f"[DB] Auto-reminder scheduled for {candidate_id} on {follow_up_date.date()}")
    return result.data[0] if result.data else payload


def get_pending_reminders() -> list:
    """Get all pending follow-up reminders."""
    client = get_client()
    today = datetime.utcnow().isoformat()
    result = (
        client.table("reminders")
        .select("*, candidates(name, email, current_title, overall_score)")
        .eq("status", "pending")
        .lte("follow_up_date", today)
        .execute()
    )
    return result.data or []


def dismiss_reminder(reminder_id: str) -> bool:
    """Mark a reminder as dismissed."""
    client = get_client()
    client.table("reminders").update({"status": "dismissed"}).eq("id", reminder_id).execute()
    return True


# ─────────────────────────────────────────────
#  MEMORY — Conversation Compaction
# ─────────────────────────────────────────────

def save_memory_snapshot(session_key: str, summary: str, full_context: dict) -> dict:
    """
    Store a compressed memory snapshot (Instant Compaction).
    Prevents context overflow in long recruiting sessions.
    """
    client = get_client()
    payload = {
        "id": str(uuid.uuid4()),
        "session_key": session_key,
        "summary": summary,
        "full_context": full_context,
        "compressed_at": datetime.utcnow().isoformat(),
    }
    result = client.table("memory_snapshots").upsert(payload, on_conflict="session_key").execute()
    return result.data[0] if result.data else payload


def load_memory_snapshot(session_key: str) -> Optional[dict]:
    """Retrieve the latest memory snapshot for a session."""
    client = get_client()
    result = (
        client.table("memory_snapshots")
        .select("*")
        .eq("session_key", session_key)
        .order("compressed_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ─────────────────────────────────────────────
#  HEALTH CHECK
# ─────────────────────────────────────────────

def health_check() -> dict:
    """Verify Supabase connectivity. Returns status dict."""
    try:
        client = get_client()
        # Lightweight query
        client.table("candidates").select("id").limit(1).execute()
        return {"status": "connected", "project": "jvsdazoxmcehnazxthwm", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"[DB] Health check failed: {e}")
        return {"status": "error", "detail": str(e)}

"""
╔══════════════════════════════════════════════════════════════╗
║  SCORE CANDIDATE — Evaluator-Optimizer Pipeline             ║
║  Runs 2-pass scoring → Generates Interview Guide PDF        ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
from fastapi.responses import Response
from dotenv import load_dotenv

import asyncio
from core.evaluator import evaluate_answers
from tools.pdf_generator import generate_interview_guide
from database.supabase_handler import (
    get_screening_session, get_candidate, save_score, schedule_reminder
)

load_dotenv()

def evaluate_screening(session_id: str, answers: list[dict]) -> dict:
    """
    Full scoring pipeline:
    1. Fetch session from Supabase (questions + candidate data)
    2. Run Evaluator-Optimizer (2-pass Gemini scoring)
    3. Generate Interview Guide PDF
    4. Store results in Supabase
    5. Auto-schedule reminder if score >= 85
    """

    # Fetch the screening session
    session = get_screening_session(session_id)
    if not session:
        raise Exception(f"Session {session_id} not found")

    questions = session.get("questions", [])
    job_description = session.get("job_description", "")
    candidate_id = session.get("candidate_id", "")

    # Map answers to questions
    qa_pairs = []
    for i, question_data in enumerate(questions):
        answer_obj = next((a for a in answers if a.get("question_id") == i + 1), {})
        qa_pairs.append({
            "question": question_data.get("question", ""),
            "answer": answer_obj.get("answer", "[No answer provided]"),
            "type": question_data.get("type", "general")
        })

    # Run Evaluator-Optimizer
    eval_result = asyncio.run(evaluate_answers(session_id, qa_pairs, job_description))

    # Fetch candidate info for PDF
    candidate = get_candidate(candidate_id) or {}

    # Build report for PDF
    pdf_report = {
        "candidate_name": candidate.get("name", "Unknown Candidate"),
        "job_title": candidate.get("current_title", ""),
        "total_score": eval_result.total_score,
        "recommendation": eval_result.recommendation,
        "technical_score": eval_result.technical_score,
        "cultural_fit_score": eval_result.cultural_fit_score,
        "behavioral_score": eval_result.behavioral_score,
        "skill_gaps": eval_result.weaknesses,
        "strengths": eval_result.strengths,
        "interview_traps": eval_result.interview_traps,
        "executive_summary": f"Candidate scored {eval_result.total_score}/100. Recommendation: {eval_result.recommendation.upper()}."
    }

    # Generate PDF (stored as bytes in Supabase or returned)
    try:
        pdf_bytes = generate_interview_guide(pdf_report)
        pdf_available = True
    except Exception:
        pdf_bytes = None
        pdf_available = False

    # Save score to Supabase
    score_record = {
        "session_id": session_id,
        "candidate_id": candidate_id,
        "total_score": eval_result.total_score,
        "recommendation": eval_result.recommendation,
        "technical_score": eval_result.technical_score,
        "cultural_fit_score": eval_result.cultural_fit_score,
        "behavioral_score": eval_result.behavioral_score,
        "strengths": eval_result.strengths,
        "weaknesses": eval_result.weaknesses,
        "interview_traps": eval_result.interview_traps,
        "validated": eval_result.validated
    }
    save_score(session_id, candidate_id, score_record)

    # Auto-reminder for high scorers (>= 85)
    if eval_result.total_score >= 85:
        from datetime import datetime, timedelta, timezone
        follow_up = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        schedule_reminder(candidate_id, eval_result.total_score, follow_up)

    return {
        "session_id": session_id,
        "candidate_id": candidate_id,
        "score": eval_result.total_score,
        "recommendation": eval_result.recommendation,
        "breakdown": {
            "technical": eval_result.technical_score,
            "cultural_fit": eval_result.cultural_fit_score,
            "behavioral": eval_result.behavioral_score
        },
        "strengths": eval_result.strengths,
        "weaknesses": eval_result.weaknesses,
        "interview_traps": eval_result.interview_traps,
        "pdf_guide_available": pdf_available,
        "pdf_download_url": f"/api/download_guide/{session_id}" if pdf_available else None,
        "auto_reminder_set": eval_result.total_score >= 85,
        "red_flash": eval_result.total_score < 60 or (eval_result.total_score < 70 and not eval_result.validated)
    }

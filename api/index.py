"""
TA Nexus — Vercel Serverless Entry Point
=========================================
Vercel requires Python serverless functions to be inside /api directory.
This file exposes the FastAPI app as the main handler.
"""

import sys
import os

# Add parent directory to path so we can import from core/, services/, etc.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────
app = FastAPI(
    title="TA Nexus — Intelligence OS",
    description="Recruitment Intelligence & Screening Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────
class HuntRequest(BaseModel):
    job_title: str
    company_domain: str
    candidate_first_name: str
    candidate_last_name: str
    location: str = "Riyadh, Saudi Arabia"

class AnalyzeRequest(BaseModel):
    candidate_id: str
    job_description: str
    candidate_ask_salary: float = 0.0

class GenerateLinkRequest(BaseModel):
    candidate_id: str
    job_id: str

class ScoreRequest(BaseModel):
    session_id: str
    answers: list[dict]

# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    return {
        "status": "operational",
        "system": "TA Nexus Intelligence OS",
        "version": "1.0.0",
        "apis": {
            "gemini":       bool(os.getenv("GEMINI_API_KEY")),
            "virustotal":   bool(os.getenv("VIRUSTOTAL_API_KEY")),
            "cloudmersive": bool(os.getenv("CLOUDMERSIVE_API_KEY")),
            "hunter":       bool(os.getenv("HUNTER_API_KEY")),
            "supabase":     bool(os.getenv("SUPABASE_URL")),
        }
    }

# ──────────────────────────────────────────────
# Generate Screening Link
# ──────────────────────────────────────────────
@app.post("/api/generate_link")
async def generate_screening_link(request: GenerateLinkRequest):
    """Worker C: Generate UUID screening link with tailored questions"""
    try:
        from generate_link import create_screening_session
        result = await create_screening_session(request.candidate_id, request.job_id)
        return result
    except Exception as e:
        raise HTTPException(500, f"Link generation failed: {str(e)}")

# ──────────────────────────────────────────────
# Score Candidate
# ──────────────────────────────────────────────
@app.post("/api/score_candidate")
async def score_candidate_answers(request: ScoreRequest):
    """Evaluator-Optimizer: Score answers → Generate Interview Guide PDF"""
    try:
        from score_candidate import evaluate_screening
        result = await evaluate_screening(request.session_id, request.answers)
        return result
    except Exception as e:
        raise HTTPException(500, f"Scoring failed: {str(e)}")

# ──────────────────────────────────────────────
# Get Session (for Candidate Portal)
# ──────────────────────────────────────────────
@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Returns screening session questions for the candidate portal"""
    try:
        from supabase import create_client
        db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        result = db.table("screening_sessions").select("*").eq("id", session_id).single().execute()
        if not result.data:
            raise HTTPException(404, "Session not found or expired")
        return result.data
    except Exception as e:
        raise HTTPException(500, str(e))

# ──────────────────────────────────────────────
# Dashboard Data
# ──────────────────────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard_data():
    """Returns all candidates sorted by score for the dashboard"""
    try:
        from supabase import create_client
        db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        result = db.table("candidates").select("*").order("overall_score", desc=True).execute()
        return {"candidates": result.data or [], "count": len(result.data or [])}
    except Exception as e:
        raise HTTPException(500, str(e))

# Vercel handler
handler = app

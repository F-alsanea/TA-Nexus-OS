"""
╔══════════════════════════════════════════════════════════╗
║          TA NEXUS — INTELLIGENCE & SCREENING OS          ║
║          Main Entry Point / Maestro Controller           ║
╚══════════════════════════════════════════════════════════╝

Routes all incoming requests through the Orchestrator.
FastAPI powers the serverless backend on Vercel.
"""

import os
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from core.orchestrator import Orchestrator
from tools.file_processor import process_cv
from database.supabase_handler import SupabaseHandler

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────
# App Initialization
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

orchestrator = Orchestrator()
db = SupabaseHandler()

# ──────────────────────────────────────────────
# Request / Response Models
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
@app.get("/health")
async def health_check():
    return {
        "status": "operational",
        "system": "TA Nexus Intelligence OS",
        "version": "1.0.0",
        "apis": {
            "gemini": bool(os.getenv("GEMINI_API_KEY")),
            "virustotal": bool(os.getenv("VIRUSTOTAL_API_KEY")),
            "cloudmersive": bool(os.getenv("CLOUDMERSIVE_API_KEY")),
            "hunter": bool(os.getenv("HUNTER_API_KEY")),
            "mailboxlayer": bool(os.getenv("MAILBOXLAYER_API_KEY")),
            "adzuna": bool(os.getenv("ADZUNA_APP_ID")),
            "marketstack": bool(os.getenv("MARKETSTACK_API_KEY")),
        }
    }

# ──────────────────────────────────────────────
# CV Upload & Processing
# ──────────────────────────────────────────────
@app.post("/api/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    """
    Step 1 of the API Symphony:
    VirusTotal scan → Cloudmersive convert → Pydantic validate
    """
    if not file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(400, "Only PDF and Word documents are accepted")

    file_bytes = await file.read()

    try:
        cv_data = await process_cv(file_bytes, file.filename)
        candidate_id = str(uuid.uuid4())
        await db.save_candidate(candidate_id, cv_data.model_dump())
        return {"candidate_id": candidate_id, "cv_data": cv_data.model_dump()}
    except Exception as e:
        raise HTTPException(500, f"CV processing failed: {str(e)}")

# ──────────────────────────────────────────────
# Full Intelligence Hunt
# ──────────────────────────────────────────────
@app.post("/api/hunt")
async def hunt_candidate(request: HuntRequest):
    """
    Worker B: LinkedIn sniper + email hunting + verification
    """
    try:
        result = await orchestrator.run_hunt(
            job_title=request.job_title,
            company_domain=request.company_domain,
            first_name=request.candidate_first_name,
            last_name=request.candidate_last_name,
            location=request.location
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Hunt failed: {str(e)}")

# ──────────────────────────────────────────────
# Full Candidate Analysis
# ──────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze_candidate(request: AnalyzeRequest):
    """
    Workers A + C + D: Strategic alignment, risk scoring, market analysis
    """
    try:
        candidate = await db.get_candidate(request.candidate_id)
        if not candidate:
            raise HTTPException(404, "Candidate not found")

        report = await orchestrator.run_analysis(
            candidate_data=candidate,
            job_description=request.job_description,
            salary_ask=request.candidate_ask_salary
        )
        return report
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

# ──────────────────────────────────────────────
# Dynamic Screener Link Generator
# ──────────────────────────────────────────────
@app.post("/api/generate_link")
async def generate_screening_link(request: GenerateLinkRequest):
    """
    Worker C: Generate UUID screening link with tailored questions
    """
    from api.generate_link import create_screening_session
    try:
        result = await create_screening_session(request.candidate_id, request.job_id)
        return result
    except Exception as e:
        raise HTTPException(500, f"Link generation failed: {str(e)}")

# ──────────────────────────────────────────────
# Score Candidate Answers
# ──────────────────────────────────────────────
@app.post("/api/score_candidate")
async def score_candidate(request: ScoreRequest, background_tasks: BackgroundTasks):
    """
    Evaluator-Optimizer: Score answers → Generate Interview Guide PDF
    """
    from api.score_candidate import evaluate_screening
    try:
        result = await evaluate_screening(request.session_id, request.answers)
        return result
    except Exception as e:
        raise HTTPException(500, f"Scoring failed: {str(e)}")

# ──────────────────────────────────────────────
# Get Screening Session (for Candidate Portal)
# ──────────────────────────────────────────────
@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Returns questions for candidate screening portal"""
    session = await db.get_screening_session(session_id)
    if not session:
        raise HTTPException(404, "Screening session not found or expired")
    return session

# ──────────────────────────────────────────────
# Dashboard Data
# ──────────────────────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard_data():
    """Returns all candidates, scores, and risks for dashboard"""
    candidates = await db.get_all_candidates_with_scores()
    return {"candidates": candidates}

# ──────────────────────────────────────────────
# Serve static UI (for local dev)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

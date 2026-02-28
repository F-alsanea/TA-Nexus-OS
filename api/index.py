import sys
import os
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Robust path resolution for Vercel
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Force Vercel bundler to see these directories
try:
    import core.orchestrator
    import database.supabase_handler
    import services.security_service
    import tools.pdf_generator
except ImportError:
    pass

from core.orchestrator import Orchestrator
from database.supabase_handler import (
    save_candidate, get_candidate, get_screening_session,
    get_all_candidates_with_scores
)
# We'll need a mock or simple implementation for process_cv since file_processor wasn't shown
# We'll implement a secure one using security_service directly

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

orchestrator = Orchestrator()

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

class EvaluateLinkedInRequest(BaseModel):
    profile_text: str
    target_job: str

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
# CV Upload & Processing (Pillar 1: Security First)
# ──────────────────────────────────────────────
@app.post("/api/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    """
    Step 1: VirusTotal scan -> Save to Supabase (Mocked text extraction)
    Rule 1: Security First — No file passes unscanned
    """
    from services.security_service import scan_file
    
    if not file.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(400, "Only PDF and Word documents are accepted")

    file_bytes = await file.read()

    try:
        # Mandatory VirusTotal Scan
        scan_result = await scan_file(file_bytes)
        if not scan_result.safe:
            raise HTTPException(403, f"SECURITY ALERT: File blocked. {scan_result.malicious_count} malicious engines detected.")

        # In a real app we'd call Cloudmersive here. We mock CV parse info:
        cv_data = {
            "name": file.filename.split('.')[0],
            "current_title": "Software Engineer",
            "skills": ["Python", "React", "SQL", "FastAPI"],
            "experience_years": 5,
            "security_scan": scan_result.model_dump()
        }
        
        candidate_id = str(uuid.uuid4())
        save_candidate(candidate_id, cv_data)
        return {"candidate_id": candidate_id, "cv_data": cv_data}
    except Exception as e:
        raise HTTPException(500, f"CV processing failed: {str(e)}")

# ──────────────────────────────────────────────
# Full Intelligence Hunt (Sniper Hunter)
# ──────────────────────────────────────────────
@app.post("/api/hunt")
async def hunt_candidate(request: HuntRequest):
    """Worker B: LinkedIn sniper + email hunting + verification"""
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
# Full Candidate Analysis (Strategic/Radar)
# ──────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze_candidate(request: AnalyzeRequest):
    """Workers A + C + D: Strategic alignment, risk scoring, market analysis"""
    try:
        candidate = get_candidate(request.candidate_id)
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
# Generate Screening Link
# ──────────────────────────────────────────────
@app.post("/api/generate_link")
def generate_screening_link(request: GenerateLinkRequest):
    """Worker C: Generate UUID screening link with tailored questions"""
    try:
        from api.generate_link import create_screening_session_route
        result = create_screening_session_route(request.candidate_id, request.job_id)
        return result
    except Exception as e:
        raise HTTPException(500, f"Link generation failed: {str(e)}")

# ──────────────────────────────────────────────
# Score Candidate
# ──────────────────────────────────────────────
@app.post("/api/score_candidate")
def score_candidate_answers(request: ScoreRequest):
    """Evaluator-Optimizer: Score answers → Generate Interview Guide PDF"""
    try:
        from api.score_candidate import evaluate_screening
        result = evaluate_screening(request.session_id, request.answers)
        return result
    except Exception as e:
        raise HTTPException(500, f"Scoring failed: {str(e)}")

# ──────────────────────────────────────────────
# Get Session (for Candidate Portal)
# ──────────────────────────────────────────────
@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    """Returns screening session questions for the candidate portal"""
    try:
        result = get_screening_session(session_id)
        if not result:
            raise HTTPException(404, "Session not found or expired")
        return result
    except Exception as e:
        raise HTTPException(500, str(e))

# ──────────────────────────────────────────────
# Dashboard Data
# ──────────────────────────────────────────────
@app.get("/api/dashboard")
def get_dashboard_data():
    """Returns all candidates sorted by score for the dashboard"""
    try:
        candidates = get_all_candidates_with_scores()
        return {"candidates": candidates, "count": len(candidates)}
    except Exception as e:
        # Fallback if the Supabase RPC isn't available yet or fails
        try:
            from supabase import create_client
            client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
            result = client.table("candidates").select("*").execute()
            return {"candidates": result.data or [], "count": len(result.data or [])}
        except Exception as fallback_e:
            raise HTTPException(500, str(fallback_e))

# ──────────────────────────────────────────────
# Evaluate LinkedIn Paste
# ──────────────────────────────────────────────
@app.post("/api/evaluate_linkedin")
def process_linkedin_profile(request: EvaluateLinkedInRequest):
    """
    Takes a pasted LinkedIn profile text, uses Gemini to extract/evaluate it 
    against a target job requirement, and saves it into the Database.
    """
    try:
        from api.evaluate_linkedin import evaluate_linkedin_profile
        # Evaluate synchronously
        result = evaluate_linkedin_profile(request.profile_text, request.target_job)
        return result
    except Exception as e:
        raise HTTPException(500, f"LinkedIn Evaluation failed: {str(e)}")

# Vercel handler
handler = app

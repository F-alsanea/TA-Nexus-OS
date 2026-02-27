"""
╔══════════════════════════════════════════════════════════════╗
║  FILE PROCESSOR — CV Security & Extraction Pipeline         ║
║  VirusTotal → Cloudmersive → Gemini Parse → Pydantic Model  ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import json
import google.generativeai as genai
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from dotenv import load_dotenv

from services.security_service import scan_file
from services.doc_service import convert_to_text

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ──────────────────────────────────────────────
# CV Data Model (Pydantic — Security Rule)
# ──────────────────────────────────────────────
class JobEntry(BaseModel):
    title: str = ""
    company: str = ""
    duration_months: int = 0
    description: str = ""


class CVData(BaseModel):
    name: str = "Unknown"
    email: str = ""
    phone: str = ""
    current_title: str = ""
    current_company: str = ""
    skills: list[str] = []
    education: list[str] = []
    job_history: list[JobEntry] = []
    total_years_experience: float = 0.0
    languages: list[str] = []
    summary: str = ""
    nationality: str = ""
    company_stock_symbol: str = ""
    security_status: str = "passed"
    extraction_method: str = "cloudmersive"
    raw_text_preview: str = ""


# ──────────────────────────────────────────────
# Gemini CV Parser
# ──────────────────────────────────────────────
async def parse_cv_with_gemini(raw_text: str) -> CVData:
    """
    Use Gemini to intelligently parse raw CV text into structured CVData.
    Handles Arabic and English CVs.
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
You are a CV parser for a recruitment intelligence system.
Extract all information from this CV text into a structured JSON format.
Handle both Arabic and English text.

CV TEXT:
{raw_text[:8000]}  

Respond ONLY with this JSON structure:
{{
  "name": "Full name",
  "email": "email@example.com",
  "phone": "+966...",
  "current_title": "Current job title",
  "current_company": "Current employer",
  "skills": ["skill1", "skill2", ...],
  "education": ["Degree, University, Year", ...],
  "job_history": [
    {{"title": "...", "company": "...", "duration_months": 24, "description": "..."}}
  ],
  "total_years_experience": 5.0,
  "languages": ["Arabic", "English"],
  "summary": "Brief professional summary in 1-2 sentences",
  "nationality": "Saudi / Egyptian / etc",
  "company_stock_symbol": "TADAWUL:2010 or empty if unknown"
}}

If you cannot find a field, use an empty string, 0, or empty array.
Only output valid JSON, nothing else.
"""

    response = model.generate_content(prompt)
    data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))

    # Map job_history to JobEntry models
    job_history = [
        JobEntry(**j) if isinstance(j, dict) else JobEntry()
        for j in data.get("job_history", [])
    ]
    data["job_history"] = job_history

    return CVData(**{k: v for k, v in data.items() if k != "job_history"}, job_history=job_history)


# ──────────────────────────────────────────────
# Full Pipeline
# ──────────────────────────────────────────────
async def process_cv(file_bytes: bytes, filename: str) -> CVData:
    """
    The full Rule-1 compliant CV processing pipeline:
    1. Compute hash → VirusTotal scan
    2. Cloudmersive convert → clean text
    3. Gemini parse → structured CVData
    4. Pydantic validation (automatic)
    """
    # Step 1: Security check
    scan_result = await scan_file(file_bytes)
    if not scan_result.safe:
        raise Exception(
            f"SECURITY ALERT 🛡️: File blocked by VirusTotal. "
            f"Threats: {scan_result.malicious_count} malicious, "
            f"{scan_result.suspicious_count} suspicious. "
            f"Threats: {scan_result.threat_names}"
        )

    # Step 2: Document conversion
    doc_result = await convert_to_text(file_bytes, filename)

    if not doc_result.raw_text or len(doc_result.raw_text.strip()) < 50:
        raise Exception("Document too short or could not be read. Please upload a valid CV.")

    # Step 3: Gemini parsing
    cv_data = await parse_cv_with_gemini(doc_result.raw_text)

    # Step 4: Enrich metadata
    cv_data.security_status = "passed"
    cv_data.extraction_method = doc_result.method_used
    cv_data.raw_text_preview = doc_result.raw_text[:300] + "..."

    return cv_data

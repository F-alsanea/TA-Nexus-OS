"""
╔═══════════════════════════════════════════════════════════════╗
║  ORCHESTRATOR — The Maestro                                  ║
║  Coordinates all 4 Workers: A (Strategic), B (Hunter),       ║
║  C (Analyst), D (Market Radar)                               ║
╚═══════════════════════════════════════════════════════════════╝
"""
import os
import asyncio
import google.generativeai as genai
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

from services.contact_service import get_contact_intelligence
from services.market_service import get_market_intelligence
from services.market_service import MarketIntelligence
from tools.sniper_logic import generate_boolean_url

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-1.5-flash"


# ──────────────────────────────────────────────
# Output Models
# ──────────────────────────────────────────────
class WorkerAReport(BaseModel):
    vision_2030_alignment: str
    strategic_notes: str
    domain_color: str  # "green", "yellow", "red"
    domain_alert: bool


class WorkerBReport(BaseModel):
    linkedin_sniper_url: str
    email_found: Optional[str]
    email_verified: bool
    outreach_method: str  # "email" or "linkedin"
    outreach_status: str


class WorkerCReport(BaseModel):
    overall_score: int  # 0-100
    skill_match_pct: float
    skill_gaps: list[str]
    strengths: list[str]
    recommendation: str  # "advance", "screen", "reject"
    risk_level: str  # "low", "medium", "high"


class WorkerDReport(BaseModel):
    market: MarketIntelligence
    salary_risk: str
    company_trend: str
    financial_alert: bool


class FullIntelligenceReport(BaseModel):
    candidate_name: str
    job_title: str
    worker_a: WorkerAReport
    worker_b: WorkerBReport
    worker_c: WorkerCReport
    worker_d: WorkerDReport
    final_decision: str  # "advance", "screen", "reject"
    red_flash: bool  # True if risk > 70%
    executive_summary: str


# ──────────────────────────────────────────────
# Gemini Helper
# ──────────────────────────────────────────────
async def call_gemini(prompt: str, system_role: str = "") -> str:
    """Call Gemini API with a prompt, return text response"""
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_role if system_role else None
    )
    response = model.generate_content(prompt)
    return response.text.strip()


# ──────────────────────────────────────────────
# Worker A — Strategic Advisor
# ──────────────────────────────────────────────
async def run_worker_a(
    candidate_data: dict,
    job_description: str
) -> WorkerAReport:
    """
    Matches the hiring decision with Saudi Vision 2030 goals.
    Monitors company domain color (Nitaqat compliance).
    """
    prompt = f"""
You are Worker A — Strategic Talent Advisor for Saudi Arabia.
Analyze this candidate and job against Saudi Vision 2030 strategic priorities.

Candidate Profile:
{candidate_data}

Job Description:
{job_description}

Respond in this exact JSON format:
{{
  "vision_2030_alignment": "HIGH/MEDIUM/LOW — explain why in 2 sentences",
  "strategic_notes": "Key strategic observation in 1-2 sentences",
  "domain_color": "green/yellow/red (Nitaqat Saudization compliance estimate)",
  "domain_alert": true/false
}}

Only output valid JSON, nothing else.
"""
    try:
        response = await call_gemini(prompt, "You are a strategic HR advisor specializing in Saudi Vision 2030 talent compliance.")
        import json
        data = json.loads(response.replace("```json", "").replace("```", "").strip())
        return WorkerAReport(**data)
    except Exception:
        return WorkerAReport(
            vision_2030_alignment="MEDIUM — Could not fully assess alignment",
            strategic_notes="Manual review recommended for Vision 2030 compliance",
            domain_color="yellow",
            domain_alert=False
        )


# ──────────────────────────────────────────────
# Worker B — The Sniper Hunter
# ──────────────────────────────────────────────
async def run_worker_b(
    job_title: str,
    company_domain: str,
    first_name: str,
    last_name: str,
    location: str
) -> WorkerBReport:
    """
    Generates LinkedIn Boolean URL + runs contact intelligence pipeline
    """
    # Run contact intelligence (Hunter + Mailboxlayer)
    contact = await get_contact_intelligence(company_domain, first_name, last_name)

    # Generate LinkedIn Boolean URL
    sniper_url = generate_boolean_url(job_title, [], location)

    return WorkerBReport(
        linkedin_sniper_url=sniper_url,
        email_found=contact.find.email,
        email_verified=contact.verify.verified if contact.verify else False,
        outreach_method=contact.outreach_method,
        outreach_status="ready" if contact.outreach_ready else "linkedin_fallback"
    )


# ──────────────────────────────────────────────
# Worker C — Intelligence Analyst
# ──────────────────────────────────────────────
async def run_worker_c(
    candidate_data: dict,
    job_description: str
) -> WorkerCReport:
    """
    Calculates score, identifies gaps, recommends next action
    """
    prompt = f"""
You are Worker C — Candidate Intelligence Analyst.

Analyze this candidate against the job description and produce a structured intelligence report.

Candidate Data:
{candidate_data}

Job Description:
{job_description}

Respond in this exact JSON format:
{{
  "overall_score": <integer 0-100>,
  "skill_match_pct": <float 0-100>,
  "skill_gaps": ["gap1", "gap2", "gap3"],
  "strengths": ["strength1", "strength2"],
  "recommendation": "advance/screen/reject",
  "risk_level": "low/medium/high"
}}

Be objective. Score 85+ means advance, 60-84 means screen, below 60 means reject.
Only output valid JSON.
"""
    try:
        response = await call_gemini(prompt, "You are an elite recruitment analyst. Be precise and data-driven.")
        import json
        data = json.loads(response.replace("```json", "").replace("```", "").strip())
        return WorkerCReport(**data)
    except Exception:
        return WorkerCReport(
            overall_score=50,
            skill_match_pct=50.0,
            skill_gaps=["Assessment could not complete — manual review needed"],
            strengths=["Profile received successfully"],
            recommendation="screen",
            risk_level="medium"
        )


# ──────────────────────────────────────────────
# The Orchestrator Class
# ──────────────────────────────────────────────
class Orchestrator:
    """
    The Maestro — coordinates all workers and produces the full report.
    """

    async def run_hunt(
        self,
        job_title: str,
        company_domain: str,
        first_name: str,
        last_name: str,
        location: str
    ) -> dict:
        """Worker B only — for quick candidate hunting"""
        report = await run_worker_b(job_title, company_domain, first_name, last_name, location)
        return report.model_dump()

    async def run_analysis(
        self,
        candidate_data: dict,
        job_description: str,
        salary_ask: float = 0.0
    ) -> dict:
        """
        Full intelligence run: Workers A + C + D in parallel, then executive summary
        """
        job_title = candidate_data.get("current_title", "Unknown Role")
        company_symbol = candidate_data.get("company_stock_symbol", None)

        # Run Workers A, C, D in parallel
        worker_a_task = run_worker_a(candidate_data, job_description)
        worker_c_task = run_worker_c(candidate_data, job_description)
        worker_d_task = get_market_intelligence(
            job_title=job_title,
            candidate_ask_salary=salary_ask,
            company_stock_symbol=company_symbol
        )

        worker_a, worker_c, market_intel = await asyncio.gather(
            worker_a_task, worker_c_task, worker_d_task
        )

        worker_d = WorkerDReport(
            market=market_intel,
            salary_risk=market_intel.salary_risk,
            company_trend=market_intel.company.trend if market_intel.company else "unknown",
            financial_alert=(market_intel.salary_risk == "high")
        )

        # Risk score for red flash logic
        risk_score = 0
        if worker_c.risk_level == "high":
            risk_score += 40
        if worker_d.salary_risk == "high":
            risk_score += 35
        if worker_a.domain_alert:
            risk_score += 25

        red_flash = risk_score >= 70

        # Final decision
        if worker_c.overall_score >= 85 and not red_flash:
            final_decision = "advance"
        elif worker_c.overall_score >= 60:
            final_decision = "screen"
        else:
            final_decision = "reject"

        # Executive summary via Gemini
        summary_prompt = f"""
Write a 3-sentence executive summary for a TA manager about this candidate:
- Score: {worker_c.overall_score}/100
- Strengths: {worker_c.strengths}
- Gaps: {worker_c.skill_gaps}
- Salary risk: {worker_d.salary_risk}
- Vision 2030 alignment: {worker_a.vision_2030_alignment}
- Recommendation: {final_decision}
Be professional and concise.
"""
        executive_summary = await call_gemini(summary_prompt)

        # Dummy worker_b for full report
        worker_b = WorkerBReport(
            linkedin_sniper_url="",
            email_found=None,
            email_verified=False,
            outreach_method="linkedin_sniper",
            outreach_status="not_run"
        )

        report = FullIntelligenceReport(
            candidate_name=candidate_data.get("name", "Unknown"),
            job_title=job_title,
            worker_a=worker_a,
            worker_b=worker_b,
            worker_c=worker_c,
            worker_d=worker_d,
            final_decision=final_decision,
            red_flash=red_flash,
            executive_summary=executive_summary
        )

        return report.model_dump()

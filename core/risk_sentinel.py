"""
╔═══════════════════════════════════════════════════════════╗
║  RISK SENTINEL — Gap & Risk Analysis Engine               ║
║  Calculates: Skill Gap, Retention Risk, Salary Risk,      ║
║  Cultural Risk                                            ║
╚═══════════════════════════════════════════════════════════╝
"""
from pydantic import BaseModel
from typing import Optional


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class SkillGapResult(BaseModel):
    required_skills: list[str]
    candidate_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]  # The RED DOTS in the dashboard
    match_percentage: float
    gap_severity: str  # "low", "medium", "high", "critical"


class RetentionRisk(BaseModel):
    avg_tenure_months: float
    job_count: int
    is_job_hopper: bool
    risk_level: str  # "low", "medium", "high"
    risk_score: float  # 0-100
    explanation: str


class SalaryRisk(BaseModel):
    candidate_ask: float
    market_average: float
    overage_pct: float
    risk_level: str  # "low", "medium", "high"
    alert: bool  # True if > 30% above market
    recommendation: str


class CulturalRisk(BaseModel):
    tone_score: float  # 0-100 (100 = perfect cultural fit)
    risk_level: str
    red_flags: list[str]
    positive_signals: list[str]


class RiskMatrix(BaseModel):
    skill_gap: SkillGapResult
    retention: RetentionRisk
    salary: SalaryRisk
    cultural: CulturalRisk
    aggregate_risk_score: float  # 0-100
    risk_color: str  # "green", "yellow", "orange", "red"
    red_flash_required: bool  # Dashboard red alert


# ──────────────────────────────────────────────
# Skill Gap Calculator
# ──────────────────────────────────────────────
def calculate_skill_gap(
    required_skills: list[str],
    candidate_skills: list[str]
) -> SkillGapResult:
    """
    Set subtraction: required - candidate = skill gaps (red dots)
    Normalizes skills to lowercase for comparison.
    """
    req_normalized = {s.lower().strip() for s in required_skills}
    cand_normalized = {s.lower().strip() for s in candidate_skills}

    matched = req_normalized & cand_normalized
    missing = req_normalized - cand_normalized

    match_pct = (len(matched) / len(req_normalized) * 100) if req_normalized else 100.0

    if match_pct >= 85:
        severity = "low"
    elif match_pct >= 65:
        severity = "medium"
    elif match_pct >= 45:
        severity = "high"
    else:
        severity = "critical"

    return SkillGapResult(
        required_skills=list(required_skills),
        candidate_skills=list(candidate_skills),
        matched_skills=list(matched),
        missing_skills=list(missing),
        match_percentage=round(match_pct, 1),
        gap_severity=severity
    )


# ──────────────────────────────────────────────
# Retention Risk Calculator
# ──────────────────────────────────────────────
def assess_retention_risk(job_history: list[dict]) -> RetentionRisk:
    """
    Analyze job history for job-hopping patterns.
    job_history: [{"title": "...", "company": "...", "duration_months": 18}, ...]
    """
    if not job_history:
        return RetentionRisk(
            avg_tenure_months=0,
            job_count=0,
            is_job_hopper=False,
            risk_level="unknown",
            risk_score=50.0,
            explanation="No job history provided"
        )

    tenures = [j.get("duration_months", 0) for j in job_history]
    avg_tenure = sum(tenures) / len(tenures) if tenures else 0
    job_count = len(job_history)

    # Job hopper = avg tenure < 18 months (1.5 years)
    is_hopper = avg_tenure < 18

    if avg_tenure >= 36:
        risk_level = "low"
        risk_score = 15.0
    elif avg_tenure >= 24:
        risk_level = "medium"
        risk_score = 40.0
    elif avg_tenure >= 12:
        risk_level = "medium"
        risk_score = 60.0
    else:
        risk_level = "high"
        risk_score = 85.0

    explanation = (
        f"Avg tenure: {avg_tenure:.0f} months across {job_count} positions. "
        f"{'⚠️ Job hopper detected — high flight risk.' if is_hopper else 'Stable career trajectory.'}"
    )

    return RetentionRisk(
        avg_tenure_months=round(avg_tenure, 1),
        job_count=job_count,
        is_job_hopper=is_hopper,
        risk_level=risk_level,
        risk_score=risk_score,
        explanation=explanation
    )


# ──────────────────────────────────────────────
# Salary Risk Calculator
# ──────────────────────────────────────────────
def assess_salary_risk(
    candidate_ask: float,
    market_average: float
) -> SalaryRisk:
    """
    Compares candidate salary ask to market benchmarks.
    >30% above market = HIGH BUDGET RISK (red alert)
    """
    if market_average <= 0:
        return SalaryRisk(
            candidate_ask=candidate_ask,
            market_average=0,
            overage_pct=0,
            risk_level="unknown",
            alert=False,
            recommendation="No market data available to assess salary risk"
        )

    overage_pct = ((candidate_ask - market_average) / market_average) * 100

    if overage_pct >= 30:
        risk_level = "high"
        alert = True
        recommendation = f"⚠️ Candidate asks {overage_pct:.0f}% above market. Negotiate down or reject based on budget."
    elif overage_pct >= 15:
        risk_level = "medium"
        alert = False
        recommendation = f"Candidate asks {overage_pct:.0f}% above market. Some negotiation expected."
    elif overage_pct >= -10:
        risk_level = "low"
        alert = False
        recommendation = "Salary expectation aligns well with market. Competitive offer likely to succeed."
    else:
        risk_level = "low"
        alert = False
        recommendation = "Candidate asks below market. Strong value proposition — move quickly."

    return SalaryRisk(
        candidate_ask=candidate_ask,
        market_average=market_average,
        overage_pct=round(overage_pct, 1),
        risk_level=risk_level,
        alert=alert,
        recommendation=recommendation
    )


# ──────────────────────────────────────────────
# Cultural Risk Analyzer
# ──────────────────────────────────────────────
def assess_cultural_risk(
    answers: list[str],
    company_values: list[str] = None
) -> CulturalRisk:
    """
    Basic NLP: checks tone of candidate answers for cultural fit signals.
    Full AI analysis is done by Gemini in the evaluator.
    This is the quick rule-based pre-filter.
    """
    if not answers:
        return CulturalRisk(
            tone_score=50.0,
            risk_level="unknown",
            red_flags=[],
            positive_signals=[]
        )

    # Red flag keywords
    red_flag_words = [
        "i don't", "i won't", "impossible", "blame", "they failed",
        "management is bad", "not my job", "i quit", "just a job"
    ]

    # Positive keywords
    positive_words = [
        "team", "collaborate", "learn", "grow", "ownership", "initiative",
        "achieve", "improve", "impact", "contribute", "passionate"
    ]

    all_text = " ".join(answers).lower()

    red_flags = [w for w in red_flag_words if w in all_text]
    positive_signals = [w for w in positive_words if w in all_text]

    base_score = 50.0
    base_score += min(len(positive_signals) * 5, 40)
    base_score -= min(len(red_flags) * 10, 40)
    tone_score = max(0, min(100, base_score))

    if tone_score >= 75:
        risk_level = "low"
    elif tone_score >= 50:
        risk_level = "medium"
    else:
        risk_level = "high"

    return CulturalRisk(
        tone_score=round(tone_score, 1),
        risk_level=risk_level,
        red_flags=red_flags,
        positive_signals=positive_signals
    )


# ──────────────────────────────────────────────
# Full Risk Matrix Builder
# ──────────────────────────────────────────────
def build_risk_matrix(
    required_skills: list[str],
    candidate_skills: list[str],
    job_history: list[dict],
    candidate_ask: float,
    market_average: float,
    answers: list[str] = None
) -> RiskMatrix:
    """
    Combines all risk sub-scores into the master Risk Matrix.
    Powers the heatmap and red flash alert in the Dashboard.
    """
    skill_gap = calculate_skill_gap(required_skills, candidate_skills)
    retention = assess_retention_risk(job_history)
    salary = assess_salary_risk(candidate_ask, market_average)
    cultural = assess_cultural_risk(answers or [])

    # Weighted aggregate risk score
    risk_weights = {
        "skill": 35,
        "retention": 25,
        "salary": 25,
        "cultural": 15
    }

    skill_risk_score = (100 - skill_gap.match_percentage)
    retention_risk_score = retention.risk_score
    salary_risk_score = 80 if salary.risk_level == "high" else 40 if salary.risk_level == "medium" else 10
    cultural_risk_score = 100 - cultural.tone_score

    aggregate = (
        skill_risk_score * risk_weights["skill"] / 100 +
        retention_risk_score * risk_weights["retention"] / 100 +
        salary_risk_score * risk_weights["salary"] / 100 +
        cultural_risk_score * risk_weights["cultural"] / 100
    )

    # Color coding for heatmap
    if aggregate < 25:
        color = "green"
    elif aggregate < 50:
        color = "yellow"
    elif aggregate < 70:
        color = "orange"
    else:
        color = "red"

    red_flash = aggregate >= 70

    return RiskMatrix(
        skill_gap=skill_gap,
        retention=retention,
        salary=salary,
        cultural=cultural,
        aggregate_risk_score=round(aggregate, 1),
        risk_color=color,
        red_flash_required=red_flash
    )

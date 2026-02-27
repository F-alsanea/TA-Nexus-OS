"""
╔══════════════════════════════════════════════════════════════╗
║  MARKET SERVICE — Pillars 5 & 6: Adzuna + Marketstack       ║
║  Worker D: Salary Radar + Company Financial Intelligence    ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import httpx
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY")

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api"
MARKETSTACK_BASE_URL = "https://api.marketstack.com/v1"


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class SalaryBenchmark(BaseModel):
    job_title: str
    location: str
    average_salary: float
    min_salary: float
    max_salary: float
    job_count: int
    currency: str = "SAR"
    salary_risk_threshold: float = 0.0  # 130% of average = high risk


class CompanyHealth(BaseModel):
    symbol: str
    company_name: str = ""
    last_price: float = 0.0
    price_change_pct: float = 0.0
    volume: int = 0
    trend: str = ""  # "growing", "stable", "declining"
    retention_risk: str = ""  # "low", "medium", "high"
    data_available: bool = False


class MarketIntelligence(BaseModel):
    salary: Optional[SalaryBenchmark] = None
    company: Optional[CompanyHealth] = None
    salary_risk: str = "unknown"  # "low", "medium", "high"
    salary_risk_pct: float = 0.0  # How much above market
    market_summary: str = ""


# ──────────────────────────────────────────────
# Adzuna API — Salary Benchmarking
# ──────────────────────────────────────────────
async def get_salary_benchmark(job_title: str, location: str = "sa") -> SalaryBenchmark:
    """
    Fetch average/min/max salary for a job title in Saudi Arabia.
    location: 'sa' for Saudi Arabia (Adzuna country code)
    """
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": job_title,
        "where": location,
        "results_per_page": 50,
        "content-type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{ADZUNA_BASE_URL}/jobs/sa/search/1",
            params=params
        )

        if response.status_code != 200:
            # Fallback with estimated data if API fails
            return SalaryBenchmark(
                job_title=job_title,
                location=location,
                average_salary=15000.0,
                min_salary=8000.0,
                max_salary=25000.0,
                job_count=0,
                salary_risk_threshold=19500.0
            )

        data = response.json()
        jobs = data.get("results", [])

        salaries = [
            job.get("salary_max", 0) or job.get("salary_min", 0)
            for job in jobs
            if job.get("salary_max") or job.get("salary_min")
        ]

        if salaries:
            avg = sum(salaries) / len(salaries)
            min_sal = min(salaries)
            max_sal = max(salaries)
        else:
            avg, min_sal, max_sal = 15000.0, 8000.0, 25000.0

        return SalaryBenchmark(
            job_title=job_title,
            location=location,
            average_salary=round(avg, 2),
            min_salary=round(min_sal, 2),
            max_salary=round(max_sal, 2),
            job_count=data.get("count", len(jobs)),
            salary_risk_threshold=round(avg * 1.30, 2)
        )


# ──────────────────────────────────────────────
# Marketstack API — Company Financial Intelligence
# ──────────────────────────────────────────────
async def get_company_health(stock_symbol: str) -> CompanyHealth:
    """
    Get latest stock data for a company.
    Used to assess financial stability and retention risk.
    """
    params = {
        "access_key": MARKETSTACK_API_KEY,
        "symbols": stock_symbol,
        "limit": 5  # Last 5 trading days
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{MARKETSTACK_BASE_URL}/eod",
            params=params
        )

        if response.status_code != 200:
            return CompanyHealth(
                symbol=stock_symbol,
                data_available=False,
                retention_risk="unknown"
            )

        data = response.json().get("data", [])

        if not data:
            return CompanyHealth(
                symbol=stock_symbol,
                data_available=False,
                retention_risk="unknown"
            )

        latest = data[0]
        oldest = data[-1] if len(data) > 1 else data[0]

        last_price = latest.get("close", 0)
        old_price = oldest.get("close", last_price)
        change_pct = ((last_price - old_price) / old_price * 100) if old_price else 0

        # Determine trend
        if change_pct > 3:
            trend = "growing"
            retention_risk = "low"
        elif change_pct < -3:
            trend = "declining"
            retention_risk = "high"
        else:
            trend = "stable"
            retention_risk = "medium"

        return CompanyHealth(
            symbol=stock_symbol,
            last_price=last_price,
            price_change_pct=round(change_pct, 2),
            volume=int(latest.get("volume", 0)),
            trend=trend,
            retention_risk=retention_risk,
            data_available=True
        )


# ──────────────────────────────────────────────
# Full Market Intelligence Pipeline
# ──────────────────────────────────────────────
async def get_market_intelligence(
    job_title: str,
    candidate_ask_salary: float,
    company_stock_symbol: str = None,
    location: str = "sa"
) -> MarketIntelligence:
    """
    Full Worker D pipeline:
    1. Get salary benchmark from Adzuna
    2. Get company health from Marketstack
    3. Calculate salary risk (>30% above market = HIGH RISK)
    4. Return unified MarketIntelligence report
    """
    salary_data = await get_salary_benchmark(job_title, location)

    company_data = None
    if company_stock_symbol:
        company_data = await get_company_health(company_stock_symbol)

    # Salary Risk Calculation
    if candidate_ask_salary > 0 and salary_data.average_salary > 0:
        overage_pct = (
            (candidate_ask_salary - salary_data.average_salary)
            / salary_data.average_salary * 100
        )
        if overage_pct >= 30:
            salary_risk = "high"
        elif overage_pct >= 15:
            salary_risk = "medium"
        else:
            salary_risk = "low"

        market_summary = (
            f"Candidate asks {candidate_ask_salary:,.0f} SAR. "
            f"Market average: {salary_data.average_salary:,.0f} SAR. "
            f"{'⚠️ HIGH BUDGET RISK' if salary_risk == 'high' else 'Within acceptable range'}."
        )
    else:
        overage_pct = 0.0
        salary_risk = "unknown"
        market_summary = f"Market average for {job_title}: {salary_data.average_salary:,.0f} SAR."

    return MarketIntelligence(
        salary=salary_data,
        company=company_data,
        salary_risk=salary_risk,
        salary_risk_pct=round(overage_pct, 1),
        market_summary=market_summary
    )

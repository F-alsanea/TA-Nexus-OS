"""
╔═════════════════════════════════════════════════════════════╗
║  CONTACT SERVICE — Pillars 3 & 4: Hunter + Mailboxlayer    ║
║  Worker B's Weapons: Find → Verify → Outreach              ║
╚═════════════════════════════════════════════════════════════╝
"""
import os
import httpx
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
MAILBOXLAYER_API_KEY = os.getenv("MAILBOXLAYER_API_KEY")

HUNTER_BASE_URL = "https://api.hunter.io/v2"
MAILBOXLAYER_BASE_URL = "https://apilayer.net/api"


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class EmailFindResult(BaseModel):
    email: Optional[str]
    confidence: int = 0
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    twitter: str = ""
    linkedin: str = ""
    found: bool = False


class EmailVerifyResult(BaseModel):
    email: str
    verified: bool
    smtp_check: bool
    mx_found: bool
    disposable: bool
    score: int  # 0-100
    status: str  # "valid", "invalid", "unknown"


class ContactIntelligence(BaseModel):
    find: EmailFindResult
    verify: Optional[EmailVerifyResult] = None
    outreach_ready: bool = False
    outreach_method: str = ""  # "email" or "linkedin_sniper"


# ──────────────────────────────────────────────
# Hunter API — Email Finder
# ──────────────────────────────────────────────
async def find_email(domain: str, first_name: str, last_name: str) -> EmailFindResult:
    """
    Use Hunter.io to find professional email for candidate.
    Searches based on company domain + candidate name.
    """
    params = {
        "domain": domain,
        "first_name": first_name,
        "last_name": last_name,
        "api_key": HUNTER_API_KEY
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{HUNTER_BASE_URL}/email-finder",
            params=params
        )

        if response.status_code != 200:
            return EmailFindResult(email=None, found=False)

        data = response.json().get("data", {})
        email = data.get("email")

        return EmailFindResult(
            email=email,
            confidence=data.get("confidence", 0),
            first_name=data.get("first_name", first_name),
            last_name=data.get("last_name", last_name),
            position=data.get("position", ""),
            twitter=data.get("twitter", "") or "",
            linkedin=data.get("linkedin", "") or "",
            found=bool(email)
        )


async def search_emails_by_domain(domain: str, limit: int = 10) -> list[dict]:
    """Search all discoverable emails at a company domain"""
    params = {
        "domain": domain,
        "limit": limit,
        "api_key": HUNTER_API_KEY
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{HUNTER_BASE_URL}/domain-search",
            params=params
        )

        if response.status_code != 200:
            return []

        data = response.json().get("data", {})
        return data.get("emails", [])


# ──────────────────────────────────────────────
# Mailboxlayer API — Email Verifier
# ──────────────────────────────────────────────
async def verify_email(email: str) -> EmailVerifyResult:
    """
    Verify email via SMTP check with Mailboxlayer.
    Ensures outreach won't bounce.
    """
    params = {
        "access_key": MAILBOXLAYER_API_KEY,
        "email": email,
        "smtp": 1,
        "format": 1
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{MAILBOXLAYER_BASE_URL}/check",
            params=params
        )

        if response.status_code != 200:
            return EmailVerifyResult(
                email=email,
                verified=False,
                smtp_check=False,
                mx_found=False,
                disposable=False,
                score=0,
                status="unknown"
            )

        data = response.json()
        smtp_ok = data.get("smtp_check", False)
        mx_ok = data.get("mx_found", False)
        disposable = data.get("disposable", False)

        score = 0
        if mx_ok:
            score += 40
        if smtp_ok:
            score += 50
        if not disposable:
            score += 10

        status = "valid" if (smtp_ok and mx_ok and not disposable) else \
                 "invalid" if not mx_ok else "unknown"

        return EmailVerifyResult(
            email=email,
            verified=smtp_ok and mx_ok,
            smtp_check=smtp_ok,
            mx_found=mx_ok,
            disposable=disposable,
            score=score,
            status=status
        )


# ──────────────────────────────────────────────
# Full Contact Intelligence Pipeline
# ──────────────────────────────────────────────
async def get_contact_intelligence(
    domain: str,
    first_name: str,
    last_name: str
) -> ContactIntelligence:
    """
    Full pipeline: Find → Verify → Recommend outreach method

    If Hunter finds email AND Mailboxlayer verifies it → outreach via email
    If email not found → fallback to LinkedIn sniper (Worker B)
    """
    find_result = await find_email(domain, first_name, last_name)

    verify_result = None
    outreach_ready = False
    outreach_method = "linkedin_sniper"

    if find_result.found and find_result.email:
        verify_result = await verify_email(find_result.email)
        if verify_result.verified:
            outreach_ready = True
            outreach_method = "email"
        else:
            # Email found but not verified — still try LinkedIn
            outreach_method = "linkedin_sniper"

    return ContactIntelligence(
        find=find_result,
        verify=verify_result,
        outreach_ready=outreach_ready,
        outreach_method=outreach_method
    )

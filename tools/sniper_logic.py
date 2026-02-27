"""
╔══════════════════════════════════════════════════════════════╗
║  SNIPER LOGIC — Worker B's LinkedIn Boolean Engine          ║
║  Generates encrypted Boolean search URLs for precision      ║
║  candidate hunting on LinkedIn/Google X-Ray                 ║
╚══════════════════════════════════════════════════════════════╝
"""
import urllib.parse
from typing import Optional


def generate_boolean_url(
    job_title: str,
    skills: list[str],
    location: str,
    years_exp: Optional[str] = None,
    exclude_terms: Optional[list[str]] = None
) -> str:
    """
    Generate a LinkedIn Boolean search URL (Google X-Ray technique).
    Returns a URL that searches LinkedIn profiles directly via Google.

    Example output:
    site:linkedin.com/in AND ("Software Engineer" OR "Backend Developer")
    AND ("Python" OR "FastAPI") AND "Riyadh"
    """
    # Build the Boolean query
    parts = ['site:linkedin.com/in']

    # Job title variations
    title_variants = [job_title]
    # Common Arabic/English variants for Saudi market
    title_map = {
        "HR Manager": ["HR Manager", "Human Resources Manager", "مدير موارد بشرية"],
        "Software Engineer": ["Software Engineer", "Backend Developer", "Full Stack Developer"],
        "Data Analyst": ["Data Analyst", "Business Analyst", "Data Scientist"],
        "Project Manager": ["Project Manager", "Program Manager", "مدير مشروع"],
        "Financial Analyst": ["Financial Analyst", "Finance Manager", "محلل مالي"],
    }
    if job_title in title_map:
        title_variants = title_map[job_title]

    title_query = " OR ".join(f'"{v}"' for v in title_variants)
    parts.append(f"({title_query})")

    # Skills
    if skills:
        skills_query = " OR ".join(f'"{s}"' for s in skills[:5])  # Max 5 skills
        parts.append(f"({skills_query})")

    # Location
    if location:
        parts.append(f'"{location}"')

    # Years experience filter
    if years_exp:
        parts.append(f'"{years_exp}"')

    # Exclusions
    if exclude_terms:
        for term in exclude_terms:
            parts.append(f'-"{term}"')

    # Exclude recruiters and students
    parts.append('-"looking for opportunities" -"open to work" -"student"')

    boolean_query = " AND ".join(parts)

    # Google X-Ray URL
    encoded_query = urllib.parse.quote(boolean_query)
    google_url = f"https://www.google.com/search?q={encoded_query}"

    # Direct LinkedIn URL
    li_query = urllib.parse.quote(" ".join([f'"{job_title}"', f'"{location}"'] + [f'"{s}"' for s in skills[:3]]))
    linkedin_url = f"https://www.linkedin.com/search/results/people/?keywords={li_query}&geoUrn=&origin=GLOBAL_SEARCH_HEADER"

    return google_url


def generate_linkedin_direct_url(
    job_title: str,
    skills: list[str],
    location: str
) -> str:
    """
    Generate a direct LinkedIn people search URL.
    """
    keywords = " ".join([job_title] + skills[:3])
    encoded = urllib.parse.quote(keywords)
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER"


def build_outreach_template(
    candidate_name: str,
    job_title: str,
    company_name: str,
    recruiter_name: str = "Talent Acquisition"
) -> dict[str, str]:
    """
    Generate personalized outreach message templates.
    Returns subject + body for email, and a LinkedIn InMail version.
    """
    email_subject = f"Exciting Opportunity — {job_title} at {company_name}"

    email_body = f"""Hi {candidate_name},

I came across your profile and was impressed by your background. We're currently looking for a talented {job_title} to join {company_name}'s growing team.

This role offers competitive compensation aligned with market rates, meaningful work in line with Saudi Vision 2030 goals, and significant growth opportunities.

Would you be open to a quick 15-minute call this week to explore if this could be a good fit?

Best regards,
{recruiter_name}
{company_name} | Talent Acquisition"""

    linkedin_message = f"""Hi {candidate_name} 👋

I noticed your profile and I'm reaching out about an exciting {job_title} opportunity at {company_name}. Your background looks like a great fit.

Would you be open to connecting? I'd love to share more details.

Best,
{recruiter_name}"""

    return {
        "email_subject": email_subject,
        "email_body": email_body,
        "linkedin_message": linkedin_message
    }

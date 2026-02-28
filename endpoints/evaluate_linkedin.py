import os
import json
import uuid
import logging
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx

from database.supabase_handler import get_client

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
generation_config = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 4096,
    "response_mime_type": "application/json",
}

class LinkedInEvaluationResponse(BaseModel):
    name: str = Field(description="Candidate's full name")
    current_title: str = Field(description="Candidate's current or last job title")
    current_company: str = Field(description="Candidate's current or last company")
    skills: List[str] = Field(description="List of 5-8 key technical and soft skills extracted")
    experience_years: float = Field(description="Estimated total years of professional experience")
    overall_score: float = Field(description="Score from 0 to 100 on how well they fit the target job")
    cultural_risk: float = Field(description="Risk score 0-100 indicating cultural fit issues based on profile tone/jumps")
    retention_risk: float = Field(description="Risk score 0-100 indicating likelihood of leaving quickly (job hopping history)")
    salary_risk: float = Field(description="Estimated salary risk 0-100 based on seniority vs typical budget")
    strengths: List[str] = Field(description="2-3 key strengths matching the job")
    gaps: List[str] = Field(description="2-3 missing skills or experiences required for the job")

def evaluate_linkedin_profile(profile_text: str, target_job: str) -> dict:
    """
    Takes a pasted LinkedIn profile text and a target job description/title.
    Uses Gemini to extract structured data and evaluate the fit.
    Saves the result as a new candidate in Supabase.
    """
    prompt = f"""
    You are an elite level Technical Recruiter and Intelligence Analyst (TA Nexus AI).
    Analyze the following pasted LinkedIn profile text against the target job requirements.
    Extract the candidate's core details and evaluate their fit.

    Target Job / Requirements: {target_job}

    LinkedIn Profile Text:
    {profile_text}
    """

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    try:
        response = model.generate_content(prompt)
        result_json = json.loads(response.text)
        
        # Ensure it matches our expected schema structure
        validated_data = LinkedInEvaluationResponse(**result_json)
        db_data = validated_data.model_dump()
        
        # Create a candidate record
        candidate_id = str(uuid.uuid4())
        client = get_client()

        payload = {
            "id": candidate_id,
            "name": db_data.get("name", "Unknown Candidate"),
            "email": "", # Usually not in public profile text
            "phone": "",
            "current_title": db_data.get("current_title", ""),
            "current_company": db_data.get("current_company", ""),
            "skills": db_data.get("skills", []),
            "cv_text": profile_text[:2000],  # Save a snippet as "CV"
            "overall_score": db_data.get("overall_score", 0),
            "retention_risk": db_data.get("retention_risk", 0),
            "salary_risk": db_data.get("salary_risk", 0),
            "cultural_risk": db_data.get("cultural_risk", 0),
            "domain_color": "green" if db_data.get("overall_score", 0) > 75 else ("yellow" if db_data.get("overall_score", 0) > 50 else "red"),
        }
        
        res = client.table("candidates").insert(payload).execute()
        
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "data": payload,
            "strengths": db_data.get("strengths", []),
            "gaps": db_data.get("gaps", [])
        }

    except Exception as e:
        logger.error(f"Failed to evaluate LinkedIn profile: {e}")
        raise ValueError(f"Evaluation failed: {str(e)}")

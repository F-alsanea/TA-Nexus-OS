"""
╔══════════════════════════════════════════════════════════════╗
║  EVALUATOR — Evaluator-Optimizer Loop                        ║
║  Scores candidate answers against ideal model (0-100)       ║
║  Two-pass: Evaluator → Validator for bias prevention        ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import json
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────
class QuestionScore(BaseModel):
    question: str
    candidate_answer: str
    ideal_answer: str
    score: int  # 0-20 per question
    feedback: str
    weakness_detected: bool


class EvaluationResult(BaseModel):
    session_id: str
    total_score: int  # 0-100
    score_breakdown: list[QuestionScore]
    strengths: list[str]
    weaknesses: list[str]
    cultural_fit_score: int  # 0-100
    technical_score: int  # 0-100
    behavioral_score: int  # 0-100
    interview_traps: list[str]  # Questions to use in live interview for weak areas
    recommendation: str  # "advance", "screen", "reject"
    validated: bool  # Was score validated by second pass?


# ──────────────────────────────────────────────
# Pass 1: Evaluator
# ──────────────────────────────────────────────
async def _evaluate_answers(
    questions_and_answers: list[dict],
    job_description: str
) -> dict:
    """First pass: score each answer individually"""
    model = genai.GenerativeModel("gemini-1.5-flash")

    qa_text = "\n".join([
        f"Q{i+1}: {qa['question']}\nCandidate Answer: {qa['answer']}"
        for i, qa in enumerate(questions_and_answers)
    ])

    prompt = f"""
You are the Evaluator in the TA Nexus Evaluator-Optimizer system.

Job Description:
{job_description}

Questions & Answers:
{qa_text}

For each question, provide a score (0-20) and the ideal professional answer.
Respond in this JSON format:
{{
  "scores": [
    {{
      "question": "...",
      "candidate_answer": "...",
      "ideal_answer": "...",
      "score": <0-20>,
      "feedback": "...",
      "weakness_detected": true/false
    }}
  ],
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "cultural_fit_score": <0-100>,
  "technical_score": <0-100>,
  "behavioral_score": <0-100>,
  "interview_traps": ["Follow-up question for weakness 1", "Follow-up question for weakness 2"]
}}

Be rigorous and unbiased. Only output valid JSON.
"""
    response = model.generate_content(prompt)
    return json.loads(response.text.strip().replace("```json", "").replace("```", ""))


# ──────────────────────────────────────────────
# Pass 2: Validator (Bias Check)
# ──────────────────────────────────────────────
async def _validate_score(first_pass_data: dict, total_score: int) -> tuple[int, bool]:
    """
    Second Gemini pass: validates the score for bias.
    Returns (validated_score, was_adjusted)
    """
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
You are the Validator in the TA Nexus Evaluator-Optimizer system.
Your job is to review a first-pass evaluation for bias and fairness.

First Pass Score: {total_score}/100
Evaluation Summary: {json.dumps(first_pass_data.get('strengths', []) + first_pass_data.get('weaknesses', []))}

Check for:
1. Halo effect (over or under-scoring due to one strong/weak answer)
2. Consistent scoring standard
3. Cultural bias

Respond in JSON:
{{
  "validated_score": <integer 0-100, adjust if needed>,
  "bias_detected": true/false,
  "adjustment_reason": "..."
}}
"""
    response = model.generate_content(prompt)
    data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    validated_score = data.get("validated_score", total_score)
    was_adjusted = abs(validated_score - total_score) > 5
    return validated_score, was_adjusted


# ──────────────────────────────────────────────
# Main Evaluation Pipeline
# ──────────────────────────────────────────────
async def evaluate_answers(
    session_id: str,
    questions_and_answers: list[dict],
    job_description: str
) -> EvaluationResult:
    """
    Full Evaluator-Optimizer pipeline:
    1. Evaluator scores each answer
    2. Validator checks for bias
    3. Returns final validated score
    """
    try:
        # Pass 1
        eval_data = await _evaluate_answers(questions_and_answers, job_description)

        scores_data = eval_data.get("scores", [])
        raw_total = sum(s.get("score", 0) for s in scores_data)
        # Normalize to 100
        max_possible = len(scores_data) * 20
        normalized_score = int((raw_total / max(max_possible, 1)) * 100)

        # Pass 2: Validate
        validated_score, was_adjusted = await _validate_score(eval_data, normalized_score)

        score_breakdown = [
            QuestionScore(
                question=s.get("question", ""),
                candidate_answer=s.get("candidate_answer", ""),
                ideal_answer=s.get("ideal_answer", ""),
                score=s.get("score", 0),
                feedback=s.get("feedback", ""),
                weakness_detected=s.get("weakness_detected", False)
            )
            for s in scores_data
        ]

        # Final recommendation
        if validated_score >= 85:
            recommendation = "advance"
        elif validated_score >= 60:
            recommendation = "screen"
        else:
            recommendation = "reject"

        return EvaluationResult(
            session_id=session_id,
            total_score=validated_score,
            score_breakdown=score_breakdown,
            strengths=eval_data.get("strengths", []),
            weaknesses=eval_data.get("weaknesses", []),
            cultural_fit_score=eval_data.get("cultural_fit_score", 50),
            technical_score=eval_data.get("technical_score", 50),
            behavioral_score=eval_data.get("behavioral_score", 50),
            interview_traps=eval_data.get("interview_traps", []),
            recommendation=recommendation,
            validated=True
        )

    except Exception as e:
        return EvaluationResult(
            session_id=session_id,
            total_score=50,
            score_breakdown=[],
            strengths=[],
            weaknesses=["Evaluation error — manual review required"],
            cultural_fit_score=50,
            technical_score=50,
            behavioral_score=50,
            interview_traps=[],
            recommendation="screen",
            validated=False
        )

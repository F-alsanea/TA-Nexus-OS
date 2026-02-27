"""
╔══════════════════════════════════════════════════════════════╗
║  MEMORY MANAGER — Context Compaction (Nexus Memory)         ║
║  Compresses long sessions → saves to Supabase               ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class MemorySnapshot(BaseModel):
    session_id: str
    summary: str
    key_facts: list[str]
    token_count_before: int
    token_count_after: int
    compression_ratio: float


async def compact_session(session_id: str, conversation_text: str) -> MemorySnapshot:
    """
    Compresses a long conversation into a structured memory snapshot.
    Uses Gemini to extract key facts and produce a dense summary.
    Implements 'Instant Compaction' rule — fires after 3000 tokens.
    """
    token_estimate_before = len(conversation_text.split())

    prompt = f"""
You are the TA Nexus Memory Compactor. Compress this conversation into an ultra-dense intelligence summary.

CONVERSATION:
{conversation_text}

Respond in this JSON format:
{{
  "summary": "Dense 2-3 sentence summary of all key information",
  "key_facts": ["fact1", "fact2", "fact3", "fact4", "fact5"]
}}

Preserve: candidate names, scores, decisions, risks, emails, and any action items.
Only output valid JSON.
"""

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    try:
        import json
        data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        summary = data.get("summary", "Session context preserved.")
        key_facts = data.get("key_facts", [])
    except Exception:
        summary = conversation_text[:500] + "..." if len(conversation_text) > 500 else conversation_text
        key_facts = []

    token_estimate_after = len(summary.split()) + sum(len(f.split()) for f in key_facts)
    compression_ratio = round(token_estimate_before / max(token_estimate_after, 1), 2)

    return MemorySnapshot(
        session_id=session_id,
        summary=summary,
        key_facts=key_facts,
        token_count_before=token_estimate_before,
        token_count_after=token_estimate_after,
        compression_ratio=compression_ratio
    )


def rebuild_context(snapshot: MemorySnapshot) -> str:
    """Rebuilds context string from a memory snapshot for injection into prompts"""
    facts_text = "\n".join(f"- {fact}" for fact in snapshot.key_facts)
    return f"""
[NEXUS MEMORY — Session {snapshot.session_id}]
Summary: {snapshot.summary}
Key Facts:
{facts_text}
"""


async def should_compact(conversation_text: str, threshold_tokens: int = 3000) -> bool:
    """Returns True if the conversation exceeds the compaction threshold"""
    estimated_tokens = len(conversation_text.split()) * 1.3  # rough token estimate
    return estimated_tokens >= threshold_tokens

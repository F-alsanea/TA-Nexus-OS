"""
╔═══════════════════════════════════════════════════════════╗
║  DOCUMENT SERVICE — Pillar 2: Cloudmersive Integration   ║
║  Converts PDF/Word CVs → Clean Text (90% token savings)  ║
╚═══════════════════════════════════════════════════════════╝
"""
import os
import base64
import httpx
import re
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

CLOUDMERSIVE_API_KEY = os.getenv("CLOUDMERSIVE_API_KEY")
CLOUDMERSIVE_BASE_URL = "https://api.cloudmersive.com"


class ExtractedDocument(BaseModel):
    raw_text: str
    word_count: int
    success: bool
    method_used: str  # "cloudmersive" or "fallback"


async def convert_pdf_to_text(file_bytes: bytes) -> str:
    """Convert PDF bytes to text via Cloudmersive Document Conversion"""
    headers = {
        "Apikey": CLOUDMERSIVE_API_KEY,
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{CLOUDMERSIVE_BASE_URL}/convert/pdf/to/txt",
            headers=headers,
            content=file_bytes
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("TextResult", "")
        else:
            raise Exception(f"Cloudmersive PDF error: {response.status_code} — {response.text}")


async def convert_docx_to_text(file_bytes: bytes) -> str:
    """Convert DOCX bytes to text via Cloudmersive"""
    headers = {
        "Apikey": CLOUDMERSIVE_API_KEY,
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{CLOUDMERSIVE_BASE_URL}/convert/word/docx/to/txt",
            headers=headers,
            content=file_bytes
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("TextResult", "")
        else:
            raise Exception(f"Cloudmersive DOCX error: {response.status_code}")


def fallback_text_extractor(file_bytes: bytes, filename: str) -> str:
    """
    Fallback when Cloudmersive rate limit is hit.
    Basic extraction using byte-level heuristics + regex.
    Dashboard will show a warning when this is used.
    """
    try:
        # Try UTF-8 decode first
        text = file_bytes.decode("utf-8", errors="ignore")
        # Strip binary garbage
        text = re.sub(r'[^\x20-\x7E\n\r\t\u0600-\u06FF]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text if len(text) > 100 else "[Fallback extraction produced minimal content]"
    except Exception:
        return "[Could not extract text from document]"


async def convert_to_text(file_bytes: bytes, filename: str) -> ExtractedDocument:
    """
    Main document conversion pipeline:
    1. Try Cloudmersive based on file type
    2. Fallback to internal extractor on rate limit / error
    """
    filename_lower = filename.lower()

    try:
        if filename_lower.endswith(".pdf"):
            text = await convert_pdf_to_text(file_bytes)
            method = "cloudmersive"
        elif filename_lower.endswith((".docx", ".doc")):
            text = await convert_docx_to_text(file_bytes)
            method = "cloudmersive"
        else:
            text = fallback_text_extractor(file_bytes, filename)
            method = "fallback"

        return ExtractedDocument(
            raw_text=text,
            word_count=len(text.split()),
            success=True,
            method_used=method
        )

    except Exception as e:
        # Rate limit or API error — use fallback
        fallback_text = fallback_text_extractor(file_bytes, filename)
        return ExtractedDocument(
            raw_text=fallback_text,
            word_count=len(fallback_text.split()),
            success=False,
            method_used="fallback"
        )

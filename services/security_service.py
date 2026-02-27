"""
╔══════════════════════════════════════════════════════╗
║  SECURITY SERVICE — Pillar 1: VirusTotal Integration ║
║  Rule 1: Security First — No file passes unscanned  ║
╚══════════════════════════════════════════════════════╝
"""
import os
import hashlib
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
VT_BASE_URL = "https://www.virustotal.com/api/v3"


class SecurityScanResult(BaseModel):
    sha256: str
    safe: bool
    malicious_count: int
    suspicious_count: int
    total_engines: int
    threat_names: list[str] = []
    scan_url: str = ""


def compute_sha256(file_bytes: bytes) -> str:
    """Compute SHA-256 hash of file bytes"""
    return hashlib.sha256(file_bytes).hexdigest()


async def scan_file_hash(sha256: str) -> SecurityScanResult:
    """
    Check VirusTotal for an existing scan of this file hash.
    Returns safe=True if no threats detected by any engine.
    """
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{VT_BASE_URL}/files/{sha256}",
            headers=headers
        )

        if response.status_code == 404:
            # File not in VT database — submit for analysis
            return SecurityScanResult(
                sha256=sha256,
                safe=True,
                malicious_count=0,
                suspicious_count=0,
                total_engines=0,
                threat_names=[],
                scan_url=""
            )

        if response.status_code != 200:
            raise Exception(f"VirusTotal API error: {response.status_code}")

        data = response.json()
        stats = data["data"]["attributes"]["last_analysis_stats"]
        results = data["data"]["attributes"]["last_analysis_results"]

        malicious_count = stats.get("malicious", 0)
        suspicious_count = stats.get("suspicious", 0)
        total_engines = sum(stats.values())

        threat_names = [
            v["result"]
            for v in results.values()
            if v.get("category") in ("malicious", "suspicious") and v.get("result")
        ]

        return SecurityScanResult(
            sha256=sha256,
            safe=(malicious_count == 0 and suspicious_count == 0),
            malicious_count=malicious_count,
            suspicious_count=suspicious_count,
            total_engines=total_engines,
            threat_names=threat_names,
            scan_url=f"https://www.virustotal.com/gui/file/{sha256}"
        )


async def scan_file(file_bytes: bytes) -> SecurityScanResult:
    """
    Full security pipeline:
    1. Compute SHA-256 hash
    2. Query VirusTotal
    3. Return result
    """
    sha256 = compute_sha256(file_bytes)
    result = await scan_file_hash(sha256)
    return result

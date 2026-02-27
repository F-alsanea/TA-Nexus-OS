"""
╔══════════════════════════════════════════════════════════════╗
║  PDF GENERATOR — Interview Guide & Candidate Card           ║
║  Outputs professional PDF with trap questions + scorecards  ║
╚══════════════════════════════════════════════════════════════╝
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ──────────────────────────────────────────────
# Color Palette
# ──────────────────────────────────────────────
NEXUS_DARK = colors.HexColor("#0D1117")
NEXUS_BLUE = colors.HexColor("#4F8EF7")
NEXUS_GOLD = colors.HexColor("#F5A623")
NEXUS_GREEN = colors.HexColor("#28A745")
NEXUS_RED = colors.HexColor("#DC3545")
NEXUS_GRAY = colors.HexColor("#6C757D")
NEXUS_LIGHT = colors.HexColor("#F8F9FA")


def generate_interview_guide(candidate_report: dict) -> bytes:
    """
    Generate a professional PDF Interview Guide.
    Contains: scorecard, skill gaps, trap questions, expected answers.
    Returns PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Custom Styles ──
    title_style = ParagraphStyle(
        "NexusTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=NEXUS_BLUE,
        spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    subtitle_style = ParagraphStyle(
        "NexusSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=NEXUS_GRAY,
        spaceAfter=16,
        fontName="Helvetica"
    )
    section_style = ParagraphStyle(
        "NexusSection",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=NEXUS_BLUE,
        spaceBefore=14,
        spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "NexusBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=4,
        fontName="Helvetica"
    )
    label_style = ParagraphStyle(
        "NexusLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=NEXUS_GRAY,
        fontName="Helvetica-Oblique"
    )

    # ── HEADER ──
    story.append(Paragraph("TA NEXUS", title_style))
    story.append(Paragraph("Confidential Interview Intelligence Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=NEXUS_BLUE))
    story.append(Spacer(1, 0.4*cm))

    # ── CANDIDATE INFO ──
    candidate_name = candidate_report.get("candidate_name", "Unknown Candidate")
    job_title = candidate_report.get("job_title", "Unknown Role")
    score = candidate_report.get("total_score", 0)
    recommendation = candidate_report.get("recommendation", "screen").upper()
    date_str = datetime.now().strftime("%d %B %Y")

    rec_color = NEXUS_GREEN if recommendation == "ADVANCE" else \
                NEXUS_GOLD if recommendation == "SCREEN" else NEXUS_RED

    info_data = [
        ["Candidate", candidate_name, "Report Date", date_str],
        ["Role", job_title, "Recommendation", recommendation],
        ["Overall Score", f"{score}/100", "Assessor", "TA Nexus AI"],
    ]
    info_table = Table(info_data, colWidths=[3.5*cm, 7*cm, 3.5*cm, 4*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NEXUS_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), NEXUS_GRAY),
        ("TEXTCOLOR", (2, 0), (2, -1), NEXUS_GRAY),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (3, 1), (3, 1), rec_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [NEXUS_LIGHT, colors.white]),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*cm))

    # ── SCORE BREAKDOWN ──
    story.append(Paragraph("📊 Score Breakdown", section_style))

    worker_c = candidate_report.get("worker_c", {})
    technical_score = candidate_report.get("technical_score", worker_c.get("overall_score", score))
    cultural_score = candidate_report.get("cultural_fit_score", 70)
    behavioral_score = candidate_report.get("behavioral_score", 65)

    score_data = [
        ["Dimension", "Score", "Rating"],
        ["Technical Skills", f"{technical_score}/100", _rating(technical_score)],
        ["Cultural Fit", f"{cultural_score}/100", _rating(cultural_score)],
        ["Behavioral", f"{behavioral_score}/100", _rating(behavioral_score)],
        ["OVERALL", f"{score}/100", _rating(score)],
    ]
    score_table = Table(score_data, colWidths=[8*cm, 4*cm, 6*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NEXUS_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EBF3FF")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, NEXUS_LIGHT]),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.4*cm))

    # ── SKILL GAPS (RED DOTS) ──
    gaps = candidate_report.get("skill_gaps", worker_c.get("skill_gaps", []))
    if gaps:
        story.append(Paragraph("🔴 Identified Skill Gaps", section_style))
        for gap in gaps:
            story.append(Paragraph(f"• {gap}", body_style))
        story.append(Spacer(1, 0.3*cm))

    # ── STRENGTHS ──
    strengths = candidate_report.get("strengths", worker_c.get("strengths", []))
    if strengths:
        story.append(Paragraph("✅ Key Strengths", section_style))
        for strength in strengths:
            story.append(Paragraph(f"• {strength}", body_style))
        story.append(Spacer(1, 0.3*cm))

    # ── TRAP QUESTIONS (Interview Guide) ──
    trap_questions = candidate_report.get("interview_traps", [])
    if trap_questions:
        story.append(HRFlowable(width="100%", thickness=1, color=NEXUS_GRAY))
        story.append(Paragraph("🎯 Recommended Interview Questions", section_style))
        story.append(Paragraph(
            "These questions target the candidate's identified weak areas. Listen carefully for depth and ownership.",
            label_style
        ))
        story.append(Spacer(1, 0.2*cm))
        for i, q in enumerate(trap_questions, 1):
            story.append(Paragraph(f"Q{i}. {q}", body_style))
            story.append(Spacer(1, 0.2*cm))

    # ── EXECUTIVE SUMMARY ──
    summary = candidate_report.get("executive_summary", "")
    if summary:
        story.append(HRFlowable(width="100%", thickness=1, color=NEXUS_BLUE))
        story.append(Paragraph("📝 Executive Summary", section_style))
        story.append(Paragraph(summary, body_style))

    # ── FOOTER ──
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NEXUS_GRAY))
    story.append(Paragraph(
        f"Generated by TA Nexus Intelligence OS • {date_str} • CONFIDENTIAL",
        label_style
    ))

    doc.build(story)
    return buffer.getvalue()


def _rating(score: int) -> str:
    if score >= 85:
        return "⭐ Excellent"
    elif score >= 70:
        return "✅ Good"
    elif score >= 55:
        return "⚠️ Fair"
    else:
        return "❌ Poor"


def generate_candidate_card(candidate_data: dict) -> bytes:
    """Generate a compact one-page candidate summary card"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = []

    name = candidate_data.get("name", "Unknown")
    title = candidate_data.get("current_title", "")
    score = candidate_data.get("score", 0)
    skills = candidate_data.get("skills", [])
    email = candidate_data.get("email", "")

    story.append(Paragraph(name, ParagraphStyle("H", fontSize=20, textColor=NEXUS_BLUE, fontName="Helvetica-Bold")))
    story.append(Paragraph(title, ParagraphStyle("S", fontSize=12, textColor=NEXUS_GRAY, fontName="Helvetica")))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Score: {score}/100 | Email: {email}", styles["Normal"]))
    story.append(Spacer(1, 0.3*cm))
    if skills:
        story.append(Paragraph("Skills: " + " • ".join(skills[:8]), styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()

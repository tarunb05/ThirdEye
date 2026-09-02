from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
import io
from datetime import datetime

# Dark theme colors
BG = HexColor("#111318")
SURFACE = HexColor("#1a1d24")
BORDER = HexColor("#2a2d35")
TEXT_PRIMARY = HexColor("#e8e6e1")
TEXT_SECONDARY = HexColor("#9ca3af")
TEXT_MUTED = HexColor("#6b7280")
EMERALD = HexColor("#34d399")
ROSE = HexColor("#fb7185")
AMBER = HexColor("#fbbf24")
BLUE = HexColor("#60a5fa")
ACCENT = HexColor("#10b981")


def _dark_bg(canvas, doc):
    """Draw dark background on every page."""
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=True, stroke=False)
    # Footer
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawCentredString(A4[0] / 2, 15 * mm, f"ThirdEye v3 · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    canvas.drawRightString(A4[0] - 25 * mm, 15 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def generate_pdf_report(code: str, result: dict) -> bytes:
    """Generate a dark-themed PDF audit report. Returns bytes."""
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=25 * mm, leftMargin=25 * mm,
        topMargin=25 * mm, bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom dark styles
    s = lambda name, **kw: styles.add(ParagraphStyle(name, **kw))
    s("DTitle", parent=styles["Title"], fontSize=32, textColor=EMERALD, fontName="Helvetica-Bold", spaceAfter=4)
    s("DSub", parent=styles["Normal"], fontSize=11, textColor=TEXT_MUTED, spaceAfter=16)
    s("DH1", parent=styles["Heading1"], fontSize=18, textColor=TEXT_PRIMARY, fontName="Helvetica-Bold", spaceBefore=20, spaceAfter=10)
    s("DH2", parent=styles["Heading2"], fontSize=13, textColor=TEXT_SECONDARY, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    s("DBody", parent=styles["Normal"], fontSize=10, textColor=TEXT_SECONDARY, leading=16, spaceAfter=8)
    s("DCode", parent=styles["Normal"], fontSize=7.5, fontName="Courier", textColor=TEXT_MUTED, leading=10, leftIndent=8, rightIndent=8, backColor=SURFACE, spaceAfter=6)
    s("DVerdictGO", parent=styles["Title"], fontSize=40, textColor=EMERALD, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4)
    s("DVerdictNO", parent=styles["Title"], fontSize=40, textColor=ROSE, alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=4)
    s("DCenter", parent=styles["Normal"], fontSize=10, textColor=TEXT_MUTED, alignment=TA_CENTER, spaceAfter=16)
    s("DSmall", parent=styles["Normal"], fontSize=8, textColor=TEXT_MUTED, spaceAfter=4)

    verdict = result.get("final_verdict", "UNKNOWN")
    vulns = result.get("vulnerabilities", [])
    summary = result.get("summary", "N/A")
    raven = result.get("raven_note", "")
    stats = result.get("stats", {})
    name = result.get("contract_name", "Unknown")

    story = []

    # Header
    story.append(Paragraph("THIRDEYE", styles["DTitle"]))
    story.append(Paragraph("Smart Contract Security Audit Report", styles["DSub"]))
    story.append(Paragraph(
        f"Contract: <b>{name}</b> &nbsp;|&nbsp; "
        f"Date: {datetime.now().strftime('%B %d, %Y')} &nbsp;|&nbsp; "
        f"Engine: Raven v3",
        styles["DSub"],
    ))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=20))

    # Verdict
    v_style = "DVerdictGO" if verdict == "GO" else "DVerdictNO"
    v_label = "PASS" if verdict == "GO" else "FAIL"
    story.append(Paragraph(v_label, styles[v_style]))
    story.append(Paragraph(
        f"Verdict: <b>{verdict}</b> &nbsp;&middot;&nbsp; "
        f"{len(vulns)} finding{'s' if len(vulns) != 1 else ''} &nbsp;&middot;&nbsp; "
        f"{stats.get('raw_llm_findings', '?')} raw / {stats.get('final_findings', len(vulns))} confirmed",
        styles["DCenter"],
    ))

    # Raven note
    if raven:
        story.append(Paragraph(f'<i>"{raven}"</i> — Raven', styles["DBody"]))
    story.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=16))

    # Summary
    story.append(Paragraph("Executive Summary", styles["DH1"]))
    story.append(Paragraph(summary, styles["DBody"]))

    # Stats table
    tdata = [
        ["Metric", "Value"],
        ["Contract", name],
        ["AI Findings (raw)", str(stats.get("raw_llm_findings", 0))],
        ["Confirmed Findings", str(stats.get("final_findings", len(vulns)))],
        ["Slither Findings", str(stats.get("slither_findings", 0))],
        ["Similar in DB", str(stats.get("similar_in_db", 0))],
        ["Verdict", verdict],
    ]
    t = Table(tdata, colWidths=[200, 240])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e2028")),
        ("TEXTCOLOR", (0, 0), (-1, 0), EMERALD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), SURFACE),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_SECONDARY),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    # Vulnerabilities
    story.append(Paragraph("Vulnerability Findings", styles["DH1"]))
    if not vulns:
        story.append(Paragraph("No vulnerabilities were detected. The contract appears to follow secure coding practices.", styles["DBody"]))
    else:
        for i, v in enumerate(vulns, 1):
            sev = v.get("severity", "unknown").upper()
            sev_color = {"CRITICAL": ROSE, "HIGH": HexColor("#fb923c"), "MEDIUM": AMBER, "LOW": BLUE}.get(sev, TEXT_MUTED)

            block = []
            block.append(Paragraph(
                f'<font color="{sev_color.hexval()}">[{sev}]</font> &nbsp; '
                f'<font color="{TEXT_PRIMARY.hexval()}"><b>#{i}: {v.get("type", "?").replace("-", " ").title()}</b></font>',
                styles["DH2"],
            ))

            parts = []
            if v.get("line"): parts.append(f"Line {v['line']}")
            conf = v.get("final_confidence", v.get("confidence", 0))
            parts.append(f"Confidence: {int(conf * 100)}%")
            if v.get("verified_by_slither"): parts.append("Verified by Slither")
            src = v.get("source", ", ".join(v.get("sources", ["llm"])))
            parts.append(f"Source: {src}")

            block.append(Paragraph(f'<font color="{TEXT_MUTED.hexval()}">{" · ".join(parts)}</font>', styles["DSmall"]))
            if v.get("description"):
                block.append(Paragraph(f'<font color="{TEXT_SECONDARY.hexval()}"><i>{v["description"]}</i></font>', styles["DBody"]))
            block.append(HRFlowable(width="100%", thickness=0.2, color=BORDER, spaceAfter=8))
            story.append(KeepTogether(block))

    # Methodology
    story.append(PageBreak())
    story.append(Paragraph("Methodology", styles["DH1"]))
    story.append(Paragraph(
        "ThirdEye uses a multi-layered analysis approach combining AI-powered code review "
        "with deterministic static analysis. The pipeline pre-analyzes the code to detect "
        "which vulnerability patterns are actually present, then queries the LLM with targeted "
        "prompts. A false-positive filter removes hallucinated findings that contradict the "
        "actual code structure. ChromaDB stores past analyses to improve accuracy over time.",
        styles["DBody"],
    ))

    mdata = [
        ["Layer", "Description"],
        ["Pre-analysis", "Regex-based pattern detection (external calls, selfdestruct, etc.)"],
        ["LLM Scan", "Targeted vulnerability analysis with anti-hallucination prompts"],
        ["False-positive filter", "Removes LLM findings that contradict actual code patterns"],
        ["Slither (optional)", "Deterministic static analysis tool"],
        ["ChromaDB", "Vector similarity search against past contract analyses"],
    ]
    mt = Table(mdata, colWidths=[120, 320])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e2028")),
        ("TEXTCOLOR", (0, 0), (-1, 0), EMERALD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), SURFACE),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_SECONDARY),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(mt)

    # Source code
    story.append(Spacer(1, 16))
    story.append(Paragraph("Analyzed Source Code", styles["DH1"]))
    lines = code.split("\n")
    numbered = []
    for i, line in enumerate(lines[:80], 1):
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        numbered.append(f"{i:3d}  {safe}")
    ctext = "\n".join(numbered)
    if len(lines) > 80:
        ctext += f"\n... ({len(lines) - 80} more lines)"
    story.append(Paragraph(ctext.replace("\n", "<br/>"), styles["DCode"]))

    # Disclaimer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=10))
    story.append(Paragraph(
        '<font color="#6b7280"><b>Disclaimer:</b> This report is generated by ThirdEye, an AI-powered '
        'analysis tool. It does not constitute a professional security audit. Always engage qualified '
        'auditors for production deployments.</font>',
        styles["DSmall"],
    ))

    doc.build(story, onFirstPage=_dark_bg, onLaterPages=_dark_bg)
    return buf.getvalue()

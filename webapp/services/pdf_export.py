from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

PAGE_W, _ = A4
MARGIN     = 2 * cm
CONTENT_W  = PAGE_W - 2 * MARGIN

COLOR_HEADER  = colors.HexColor("#1E3A5F")
COLOR_RISK    = colors.HexColor("#DC3545")
COLOR_SAFE    = colors.HexColor("#28A745")
COLOR_ACCENT  = colors.HexColor("#2C5F8A")
COLOR_ROW_ALT = colors.HexColor("#F4F6F8")
COLOR_BORDER  = colors.HexColor("#DEE2E6")
COLOR_TEXT    = colors.HexColor("#212529")
COLOR_MUTED   = colors.HexColor("#6C757D")
COLOR_WHITE   = colors.white


def _base_styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle(
            "h1", parent=base["Normal"],
            fontSize=16, textColor=COLOR_WHITE,
            leading=20, spaceAfter=2,
        ),
        "h1sub": ParagraphStyle(
            "h1sub", parent=base["Normal"],
            fontSize=9, textColor=colors.HexColor("#A8C0D6"),
            leading=12,
        ),
        "section": ParagraphStyle(
            "section", parent=base["Normal"],
            fontSize=10, textColor=COLOR_ACCENT,
            spaceBefore=14, spaceAfter=5,
            leading=13, fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, textColor=COLOR_TEXT, leading=13,
        ),
        "rec": ParagraphStyle(
            "rec", parent=base["Normal"],
            fontSize=9, textColor=COLOR_TEXT,
            leading=14, leftIndent=10, spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=8, textColor=COLOR_MUTED, alignment=1,
        ),
        "risk_high": ParagraphStyle(
            "risk_high", parent=base["Normal"],
            fontSize=11, textColor=COLOR_RISK,
            fontName="Helvetica-Bold", leading=14,
        ),
        "risk_safe": ParagraphStyle(
            "risk_safe", parent=base["Normal"],
            fontSize=11, textColor=COLOR_SAFE,
            fontName="Helvetica-Bold", leading=14,
        ),
    }


def _page_header(title_line, subtitle_line):
    s = _base_styles()
    header = Table(
        [[Paragraph(title_line, s["h1"])],
         [Paragraph(subtitle_line, s["h1sub"])]],
        colWidths=[CONTENT_W],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_HEADER),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
    ]))
    return header


def _kv_table(rows):
    s = _base_styles()
    col_l = CONTENT_W * 0.42
    col_r = CONTENT_W * 0.58
    data = [
        [Paragraph(f"<b>{k}</b>", s["body"]), Paragraph(str(v), s["body"])]
        for k, v in rows
    ]
    t = Table(data, colWidths=[col_l, col_r])
    t.setStyle(TableStyle([
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_WHITE, COLOR_ROW_ALT]),
        ("GRID",           (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ("TEXTCOLOR",      (0, 0), (-1, -1), COLOR_TEXT),
    ]))
    return t


def _section(title):
    s = _base_styles()
    return [
        Spacer(1, 6),
        Paragraph(title.upper(), s["section"]),
        HRFlowable(width=CONTENT_W, thickness=0.5, color=COLOR_ACCENT, spaceAfter=4),
    ]


def _footer(story):
    s = _base_styles()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.3, color=COLOR_BORDER))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Student Dropout Prediction System — IE501.F2 &nbsp;|&nbsp; Generated {ts}",
        s["footer"],
    ))


def generate_student_report_pdf(student, recommendations):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )

    s    = _base_styles()
    risk = student.get("risk", 0)
    story = []

    risk_label = "HIGH RISK" if risk else "SAFE"
    story.append(_page_header(
        f"Student Risk Report — {student.get('id', 'Unknown')}",
        f"Risk status: {risk_label}",
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"● {risk_label}",
        s["risk_high"] if risk else s["risk_safe"],
    ))
    story.append(Spacer(1, 8))

    story.extend(_section("Academic Performance"))
    days_early = student.get("avg_days_early", 0)
    timing_str = (
        f"{abs(days_early):.1f} days early" if days_early > 0
        else f"{abs(days_early):.1f} days late" if days_early < 0
        else "on deadline"
    )
    story.append(_kv_table([
        ("Average Score",          f"{student.get('score', 0):.1f} / 100"),
        ("Weighted Score",         f"{student.get('weighted_score', 0):.1f} / 100"),
        ("Submission Rate",        f"{student.get('submission_rate', 0):.0%}"),
        ("Avg Submission Timing",  timing_str),
    ]))

    story.extend(_section("VLE Engagement"))
    clicks = student.get("clicks", 0)
    active = student.get("active_days", 0)
    cpa    = f"{clicks / active:.1f}" if active else "—"
    story.append(_kv_table([
        ("Total Clicks",       f"{int(clicks):,}"),
        ("Active Days",        str(active)),
        ("Clicks / Active Day", cpa),
        ("Forum Clicks",       f"{int(student.get('forum_clicks', 0)):,}"),
        ("Resource Clicks",    f"{int(student.get('resource_clicks', 0)):,}"),
        ("Quiz Clicks",        f"{int(student.get('quiz_clicks', 0)):,}"),
    ]))

    story.extend(_section("Student Background"))
    story.append(_kv_table([
        ("Previous Attempts", str(student.get("num_prev_attempts", 0))),
        ("Formally Withdrew", "Yes" if student.get("withdrew_early") else "No"),
    ]))

    story.extend(_section("Risk Analysis & Recommended Actions"))
    for rec in recommendations:
        story.append(Paragraph(f"• {rec}", s["rec"]))

    _footer(story)
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_cohort_report_pdf(students):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )

    s = _base_styles()
    story = []

    total   = len(students)
    at_risk = [st for st in students if st.get("risk") == 1]
    safe    = total - len(at_risk)
    pct     = len(at_risk) / total * 100 if total else 0

    story.append(_page_header(
        "Cohort Risk Summary Report",
        f"{total:,} students — {datetime.now().strftime('%Y-%m-%d')}",
    ))
    story.append(Spacer(1, 10))

    story.extend(_section("Overview"))
    avg_score  = sum(st.get("score", 0) for st in students) / total if total else 0
    avg_clicks = sum(st.get("clicks", 0) for st in students) / total if total else 0
    story.append(_kv_table([
        ("Total Students",   f"{total:,}"),
        ("High Risk",        f"{len(at_risk):,}  ({pct:.1f}%)"),
        ("Safe",             f"{safe:,}  ({100 - pct:.1f}%)"),
        ("Avg Score",        f"{avg_score:.1f} / 100"),
        ("Avg Total Clicks", f"{avg_clicks:,.0f}"),
    ]))

    story.extend(_section("Top 50 Highest-Risk Students"))

    top = sorted(at_risk, key=lambda x: x.get("score", 100))[:50]

    if top:
        col_w = [
            CONTENT_W * 0.22, CONTENT_W * 0.10, CONTENT_W * 0.10,
            CONTENT_W * 0.13, CONTENT_W * 0.13, CONTENT_W * 0.17, CONTENT_W * 0.15,
        ]
        header_row = [
            Paragraph(f"<b>{h}</b>", s["body"])
            for h in ["Student ID", "Score", "Clicks", "Active Days",
                      "Sub. Rate", "Prev. Attempts", "Withdrew"]
        ]
        data = [header_row] + [
            [
                Paragraph(st.get("id", ""), s["body"]),
                Paragraph(f"{st.get('score', 0):.1f}", s["body"]),
                Paragraph(f"{int(st.get('clicks', 0)):,}", s["body"]),
                Paragraph(str(st.get("active_days", 0)), s["body"]),
                Paragraph(f"{st.get('submission_rate', 0):.0%}", s["body"]),
                Paragraph(str(st.get("num_prev_attempts", 0)), s["body"]),
                Paragraph("Yes" if st.get("withdrew_early") else "No", s["body"]),
            ]
            for st in top
        ]
        t = Table(data, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), COLOR_HEADER),
            ("TEXTCOLOR",      (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("TOPPADDING",     (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
            ("LEFTPADDING",    (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_ROW_ALT]),
            ("GRID",           (0, 0), (-1, -1), 0.3, COLOR_BORDER),
            ("TEXTCOLOR",      (0, 1), (-1, -1), COLOR_TEXT),
        ]))
        story.append(t)
    else:
        story.append(Paragraph(
            "No high-risk students found in the current dataset.", s["body"]
        ))

    _footer(story)
    doc.build(story)
    buffer.seek(0)
    return buffer
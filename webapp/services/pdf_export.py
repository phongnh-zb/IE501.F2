from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from webapp.services.cache import summarize_students_by_id

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

_RISK_LABEL = {0: "Safe", 1: "Watch", 2: "High Risk", 3: "Critical"}
_RISK_COLOR = {
    0: colors.HexColor("#059669"),
    1: colors.HexColor("#D97706"),
    2: colors.HexColor("#EA580C"),
    3: colors.HexColor("#DC2626"),
}
_GENDER = {"M": "Male", "F": "Female"}


def _risk_int(st):
    r = st.get("risk", 0)
    try:
        r = int(r)
    except (TypeError, ValueError):
        r = 0
    return max(0, min(3, r))


def _per_student_metric_means(enrollment_rows):
    by_id = {}
    for st in enrollment_rows:
        sid = st.get("id")
        if not sid:
            continue
        by_id.setdefault(sid, []).append(st)
    if not by_id:
        return 0.0, 0.0, 0.0
    score_sum = eng_sum = clk_sum = 0.0
    for rows in by_id.values():
        n = len(rows) or 1
        score_sum += sum(r.get("score", 0) or 0 for r in rows) / n
        eng_sum   += sum(r.get("engagement_ratio", 0) or 0 for r in rows) / n
        clk_sum   += sum(r.get("clicks", 0) or 0 for r in rows) / n
    m = len(by_id)
    return score_sum / m, eng_sum / m, clk_sum / m


def _representative_row_per_student(enrollment_rows):
    by_id = {}
    for st in enrollment_rows:
        sid = st.get("id")
        if not sid:
            continue
        by_id.setdefault(sid, []).append(st)

    reps = []
    for rows in by_id.values():
        worst    = max(_risk_int(r) for r in rows)
        at_worst = [r for r in rows if _risk_int(r) == worst]
        pick     = min(
            at_worst,
            key=lambda x: (x.get("score", 100), x.get("code_module", ""), x.get("code_presentation", "")),
        )
        row = dict(pick)
        row["risk"] = worst
        reps.append(row)
    return reps


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
        "muted": ParagraphStyle(
            "muted", parent=base["Normal"],
            fontSize=8, textColor=COLOR_MUTED, leading=11, spaceAfter=2,
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
        "risk_label": ParagraphStyle(
            "risk_label", parent=base["Normal"],
            fontSize=11, fontName="Helvetica-Bold", leading=14,
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
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width=CONTENT_W, thickness=0.3, color=COLOR_BORDER))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Student Dropout Prediction System &nbsp;|&nbsp; Generated {ts}",
        s["footer"],
    ))


def _data_table(header_labels, col_widths, data_rows, s):
    # Header styles are applied AFTER ROWBACKGROUNDS so they are never
    # overridden when the table breaks across pages and the header is repeated.
    header_row = [Paragraph(f"<b>{h}</b>", s["body"]) for h in header_labels]
    data = [header_row] + data_rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
        # Body rows first
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_WHITE, COLOR_ROW_ALT]),
        ("GRID",           (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ("TEXTCOLOR",      (0, 1), (-1, -1), COLOR_TEXT),
        # Header styles last — override ROWBACKGROUNDS for row 0 on every page
        ("BACKGROUND",     (0, 0), (-1, 0), COLOR_ACCENT),
        ("TEXTCOLOR",      (0, 0), (-1, 0), COLOR_WHITE),
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    return t


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

    risk_label = _RISK_LABEL.get(risk, "Unknown")
    story.append(_page_header(
        f"Student Risk Report — {student.get('id', 'Unknown')}",
        f"Module: {student.get('code_module', '—')} {student.get('code_presentation', '')}  |  Risk: {risk_label}",
    ))
    story.append(Spacer(1, 10))

    risk_style = ParagraphStyle(
        "risk_inline", parent=s["risk_label"],
        textColor=_RISK_COLOR.get(risk, COLOR_TEXT),
    )
    story.append(Paragraph(f"● {risk_label}", risk_style))
    story.append(Spacer(1, 8))

    story.extend(_section("Academic Performance"))
    days_early = student.get("avg_days_early", 0)
    timing_str = (
        f"{abs(days_early):.1f} days early" if days_early > 0
        else f"{abs(days_early):.1f} days late" if days_early < 0
        else "on deadline"
    )
    story.append(_kv_table([
        ("Average Score",         f"{student.get('score',          0):.2f} / 100"),
        ("Weighted Score",        f"{student.get('weighted_score',  0):.2f} / 100"),
        ("Exam Score",            f"{student.get('exam_score',      0):.2f} / 100"),
        ("TMA Score",             f"{student.get('tma_score',       0):.2f} / 100"),
        ("CMA Score",             f"{student.get('cma_score',       0):.2f} / 100"),
        ("Submission Rate",       f"{student.get('submission_rate', 0):.0%}"),
        ("Avg Submission Timing", timing_str),
    ]))

    story.extend(_section("VLE Engagement"))
    clicks = student.get("clicks", 0)
    active = student.get("active_days", 0)
    cpa    = f"{clicks / active:.1f}" if active else "—"
    eng    = student.get("engagement_ratio", 0)
    story.append(_kv_table([
        ("Engagement Ratio",   f"{eng * 100:.1f}%"),
        ("Active Days",        str(active)),
        ("Active Weeks",       str(student.get("active_weeks", 0))),
        ("Total Clicks",       f"{int(clicks):,}"),
        ("Clicks / Active Day", cpa),
        ("Forum Clicks",       f"{int(student.get('forum_clicks',    0)):,}"),
        ("Quiz Clicks",        f"{int(student.get('quiz_clicks',     0)):,}"),
        ("Resource Clicks",    f"{int(student.get('resource_clicks', 0)):,}"),
    ]))

    story.extend(_section("Student Background"))
    gender         = _GENDER.get(student.get("gender", ""), student.get("gender", "—") or "—")
    disability_raw = student.get("disability", "")
    disability     = "Yes" if disability_raw == "Y" else "No" if disability_raw == "N" else "—"
    imd            = student.get("imd_band") or "—"
    story.append(_kv_table([
        ("Gender",            gender),
        ("Age Band",          student.get("age_band",           "—") or "—"),
        ("Region",            student.get("region",             "—") or "—"),
        ("Highest Education", student.get("highest_education",  "—") or "—"),
        ("IMD Band",          imd),
        ("Disability",        disability),
        ("Studied Credits",   str(student.get("studied_credits", "—"))),
        ("Prev Attempts",     str(student.get("num_prev_attempts", 0))),
        ("Days Before Start", f"{int(student.get('days_before_start', 0))} days"),
        ("Formally Withdrew", "Yes" if student.get("withdrew_early") else "No"),
    ]))

    story.extend(_section("Risk Analysis & Recommended Actions"))
    for rec in recommendations:
        text = rec.get("text", rec) if isinstance(rec, dict) else rec
        story.append(Paragraph(f"• {text}", s["rec"]))

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

    agg        = summarize_students_by_id(students)
    total      = agg["unique_students"]
    n_crit     = agg["critical"]
    n_high     = agg["high_risk"]
    n_watch    = agg["watch"]
    n_safe     = agg["safe"]
    n_at_risk  = n_crit + n_high
    pct_at_risk = n_at_risk / total * 100 if total else 0.0

    avg_score, avg_eng, avg_clicks = _per_student_metric_means(students)
    reps = _representative_row_per_student(students)

    story.append(_page_header(
        "Cohort Risk Summary Report",
        f"{total:,} unique students — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ))
    story.append(Spacer(1, 10))

    story.extend(_section("Overview"))
    story.append(Paragraph(
        "Each student counted once (worst tier across modules). "
        "Averages are per-student means across enrollments, then cohort mean.",
        s["muted"],
    ))
    story.append(Spacer(1, 6))
    story.append(_kv_table([
        ("Total Students",   f"{total:,}"),
        ("Critical",         f"{n_crit:,}  ({n_crit/total*100:.1f}%)" if total else "0"),
        ("High Risk",        f"{n_high:,}  ({n_high/total*100:.1f}%)" if total else "0"),
        ("Watch",            f"{n_watch:,}  ({n_watch/total*100:.1f}%)" if total else "0"),
        ("Safe",             f"{n_safe:,}  ({n_safe/total*100:.1f}%)" if total else "0"),
        ("High + Critical",  f"{n_at_risk:,}  ({pct_at_risk:.1f}%)"),
        ("Avg Score",        f"{avg_score:.1f} / 100"),
        ("Avg Engagement",   f"{avg_eng * 100:.1f}%"),
        ("Avg Total Clicks", f"{avg_clicks:,.0f}"),
    ]))

    story.extend(_section("Top 50 Highest Risk Students"))

    at_risk_reps = [r for r in reps if r.get("risk", 0) >= 2]
    top = sorted(
        at_risk_reps,
        key=lambda x: (-_risk_int(x), x.get("score", 100)),
    )[:50]

    if top:
        col_w = [
            CONTENT_W * 0.18, CONTENT_W * 0.12, CONTENT_W * 0.10,
            CONTENT_W * 0.12, CONTENT_W * 0.13, CONTENT_W * 0.12,
            CONTENT_W * 0.11, CONTENT_W * 0.12,
        ]
        data_rows = [
            [
                Paragraph(st.get("id", ""), s["body"]),
                Paragraph(_RISK_LABEL.get(st.get("risk", 0), "—"), s["body"]),
                Paragraph(f"{st.get('score', 0):.1f}", s["body"]),
                Paragraph(f"{st.get('submission_rate', 0):.0%}", s["body"]),
                Paragraph(f"{st.get('engagement_ratio', 0) * 100:.1f}%", s["body"]),
                Paragraph(str(st.get("active_days", 0)), s["body"]),
                Paragraph(str(st.get("num_prev_attempts", 0)), s["body"]),
                Paragraph("Yes" if st.get("withdrew_early") else "No", s["body"]),
            ]
            for st in top
        ]
        story.append(_data_table(
            ["Student ID", "Risk", "Score", "Sub. Rate",
             "Engagement", "Active Days", "Prev. Att.", "Withdrew"],
            col_w,
            data_rows,
            s,
        ))
    else:
        story.append(Paragraph(
            "No high-risk or critical students found in the current dataset.", s["body"]
        ))

    _footer(story)
    doc.build(story)
    buffer.seek(0)
    return buffer
import csv
import io
from datetime import datetime

_GENDER     = {"M": "Male", "F": "Female"}
_RISK_LABEL = {0: "Safe", 1: "Watch", 2: "High Risk", 3: "Critical"}

STUDENT_CSV_COLUMNS = [
    # Identity
    ("id",                "Student ID"),
    ("code_module",       "Module"),
    ("code_presentation", "Presentation"),
    # Risk
    ("risk_label",        "Risk Tier"),
    ("final_result",      "Final Result"),
    # Demographics  (formatted to match the panel display)
    ("gender",            "Gender"),
    ("age_band",          "Age Band"),
    ("region",            "Region"),
    ("highest_education", "Highest Education"),
    ("imd_band",          "IMD Band"),
    ("disability",        "Disability"),
    ("studied_credits",   "Studied Credits"),
    ("num_prev_attempts", "Prev Attempts"),
    ("days_before_start", "Days Before Start"),
    # Academic
    ("score",             "Avg Score"),
    ("weighted_score",    "Weighted Score"),
    ("exam_score",        "Exam Score"),
    ("tma_score",         "TMA Score"),
    ("cma_score",         "CMA Score"),
    ("submission_rate",   "Submission Rate"),
    ("avg_days_early",    "Avg Days Early"),
    # Engagement
    ("engagement_ratio",  "Engagement Ratio"),
    ("active_days",       "Active Days"),
    ("active_weeks",      "Active Weeks"),
    ("clicks",            "Total Clicks"),
    ("forum_clicks",      "Forum Clicks"),
    ("quiz_clicks",       "Quiz Clicks"),
    ("resource_clicks",   "Resource Clicks"),
    # Status
    ("withdrew_early",    "Withdrew Early"),
]


def _format(field, row):
    v = row.get(field)

    # Categorical → human-readable labels (consistent with the student detail panel)
    if field == "gender":
        return _GENDER.get(v, v or "")
    if field == "disability":
        return "Yes" if v == "Y" else "No" if v == "N" else ""
    if field == "withdrew_early":
        return "Yes" if v == 1 else "No"

    # Percentages — formatted the same way the panel shows them
    if field == "submission_rate":
        return f"{round((v or 0) * 100)}%" if v is not None else ""
    if field == "engagement_ratio":
        return f"{(v or 0) * 100:.1f}%" if v is not None else ""

    # Numeric precision matching panel fields
    if field in ("score", "weighted_score", "exam_score", "tma_score", "cma_score"):
        return f"{v:.2f}" if v is not None else ""
    if field == "avg_days_early":
        return f"{v:.1f}" if v is not None else ""
    if field == "days_before_start":
        return str(round(v)) if v is not None else ""

    return "" if v is None else v


def generate_students_csv(rows):
    """
    Yield CSV lines for a list of student cache-row dicts.
    Values are formatted to match what the student detail panel displays.
    Uses a generator so Flask can stream without buffering the full dataset.

    Args:
        rows: list of student dicts from get_data_from_memory()

    Yields:
        str: one CSV line at a time (header first, then data rows)
    """
    buf    = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow([label for _, label in STUDENT_CSV_COLUMNS])
    yield buf.getvalue()

    for row in rows:
        buf.seek(0)
        buf.truncate()
        writer.writerow([_format(field, row) for field, _ in STUDENT_CSV_COLUMNS])
        yield buf.getvalue()


def csv_filename(prefix="students_export"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.csv"
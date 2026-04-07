import csv
import io
from datetime import datetime

# Ordered columns written to every student CSV export.
# field = key in the cache row dict; label = CSV header string.
STUDENT_CSV_COLUMNS = [
    ("id",                "Student ID"),
    ("code_module",       "Module"),
    ("code_presentation", "Presentation"),
    ("risk_label",        "Risk Tier"),
    ("score",             "Avg Score"),
    ("submission_rate",   "Submission Rate"),
    ("active_days",       "Active Days"),
    ("clicks",            "Total Clicks"),
    ("forum_clicks",      "Forum Clicks"),
    ("quiz_clicks",       "Quiz Clicks"),
    ("resource_clicks",   "Resource Clicks"),
    ("weighted_score",    "Weighted Score"),
    ("avg_days_early",    "Avg Days Early"),
    ("num_prev_attempts", "Prev Attempts"),
    ("withdrew_early",    "Withdrew Early"),
]


def generate_students_csv(rows):
    """
    Yield CSV lines for a list of student cache-row dicts.
    Uses a generator so Flask can stream the response without
    buffering the full dataset in memory.

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
        writer.writerow([row.get(field, "") for field, _ in STUDENT_CSV_COLUMNS])
        yield buf.getvalue()


def csv_filename(prefix="students_export"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.csv"
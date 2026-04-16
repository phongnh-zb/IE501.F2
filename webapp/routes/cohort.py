from collections import defaultdict

from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from webapp.services.cache import SYSTEM_CACHE, get_filter_options
from webapp.services.pdf_export import generate_cohort_report_pdf

cohort_bp = Blueprint("cohort", __name__)

_EMPTY_COHORT = {
    "health": {
        "enrollments": 0, "unique_students": 0,
        "critical": 0, "high_risk": 0, "watch": 0, "safe": 0,
        "withdrawal_rate": 0.0, "reattempt_rate": 0.0,
        "avg_score": 0.0, "avg_engagement": 0.0,
    },
    "score_distribution": [],
    "risk_driver":         [],
    "age_band":            [],
    "education":           [],
}


def _visible_rows(module=None, presentation=None):
    data = SYSTEM_CACHE.get("data", [])
    if not (current_user.is_admin or not current_user.modules):
        data = [r for r in data if r.get("code_module", "") in current_user.modules]
    if module:
        data = [r for r in data if r.get("code_module") == module]
    if presentation:
        data = [r for r in data if r.get("code_presentation") == presentation]
    return data


def _compute_cohort(rows):
    n = len(rows)
    if not n:
        return None

    unique_students = len({r["id"] for r in rows})
    withdrew        = sum(1 for r in rows if r.get("withdrew_early") == 1)
    reattempts      = sum(1 for r in rows if (r.get("num_prev_attempts") or 0) > 0)
    tier_counts     = {0: 0, 1: 0, 2: 0, 3: 0}
    for r in rows:
        tier_counts[r.get("risk", 0)] += 1

    avg_score = sum(r.get("score", 0) for r in rows) / n
    avg_eng   = sum(r.get("engagement_ratio", 0) for r in rows) / n

    buckets = [
        {"label": f"{i * 10}–{i * 10 + 10}", "crit": 0, "high": 0, "watch": 0, "safe": 0}
        for i in range(10)
    ]
    _tier_key = {0: "safe", 1: "watch", 2: "high", 3: "crit"}
    for r in rows:
        idx = min(int((r.get("score") or 0) // 10), 9)
        buckets[idx][_tier_key[r.get("risk", 0)]] += 1

    tier_rows = {0: [], 1: [], 2: [], 3: []}
    for r in rows:
        tier_rows[r.get("risk", 0)].append(r)

    def _avg(lst):
        if not lst:
            return None
        m = len(lst)
        return {
            "count":           m,
            "avg_score":       round(sum(x.get("score",          0) for x in lst) / m, 1),
            "avg_submission":  round(sum(x.get("submission_rate", 0) for x in lst) / m, 3),
            "avg_engagement":  round(sum(x.get("engagement_ratio",0) for x in lst) / m, 3),
            "avg_active_days": round(sum(x.get("active_days",    0) for x in lst) / m, 1),
        }

    risk_driver = []
    for tier, label in [(3, "Critical"), (2, "High Risk"), (1, "Watch"), (0, "Safe")]:
        avg = _avg(tier_rows[tier])
        if avg:
            risk_driver.append({"tier": tier, "label": label, **avg})

    age_map = defaultdict(lambda: {0: 0, 1: 0, 2: 0, 3: 0})
    for r in rows:
        age_map[r.get("age_band") or "Unknown"][r.get("risk", 0)] += 1
    _AGE_ORDER = ["0-35", "35-55", "55<=", "Unknown"]
    age_band = [
        {"band": b, "safe": age_map[b][0], "watch": age_map[b][1],
         "high": age_map[b][2], "crit": age_map[b][3]}
        for b in _AGE_ORDER if b in age_map
    ] + [
        {"band": b, "safe": v[0], "watch": v[1], "high": v[2], "crit": v[3]}
        for b, v in age_map.items() if b not in _AGE_ORDER
    ]

    edu_map = defaultdict(lambda: {0: 0, 1: 0, 2: 0, 3: 0})
    for r in rows:
        edu_map[r.get("highest_education") or "Unknown"][r.get("risk", 0)] += 1
    education = [
        {"level": edu, "safe": v[0], "watch": v[1], "high": v[2], "crit": v[3]}
        for edu, v in sorted(edu_map.items())
    ]

    return {
        "health": {
            "enrollments":     n,
            "unique_students": unique_students,
            "critical":        tier_counts[3],
            "high_risk":       tier_counts[2],
            "watch":           tier_counts[1],
            "safe":            tier_counts[0],
            "withdrawal_rate": round(withdrew   / n, 3),
            "reattempt_rate":  round(reattempts / n, 3),
            "avg_score":       round(avg_score,  1),
            "avg_engagement":  round(avg_eng,    3),
        },
        "score_distribution": buckets,
        "risk_driver":        risk_driver,
        "age_band":           age_band,
        "education":          education,
    }


def _pdf_filename():
    from datetime import datetime
    return f"cohort_risk_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"


# ── Page route ────────────────────────────────────────────────────────────────

@cohort_bp.route("/cohort")
@login_required
def cohort():
    filter_options = get_filter_options(
        modules=None if current_user.is_admin else current_user.modules
    )
    return render_template(
        "cohort/index.html",
        modules_available       = filter_options["modules"],
        presentations_available = filter_options["presentations"],
        last_updated            = SYSTEM_CACHE.get("last_updated"),
    )


# ── API routes ────────────────────────────────────────────────────────────────

@cohort_bp.route("/api/cohort/data")
@login_required
def cohort_data():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"error": "Data not ready"}), 503

    module       = request.args.get("module",       "", type=str).strip() or None
    presentation = request.args.get("presentation", "", type=str).strip() or None

    rows   = _visible_rows(module=module, presentation=presentation)
    result = _compute_cohort(rows)
    return jsonify(result or _EMPTY_COHORT)


@cohort_bp.route("/api/cohort/report")
@login_required
def cohort_report():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"error": "Data not ready — run the pipeline first"}), 503

    module       = request.args.get("module",       "", type=str).strip() or None
    presentation = request.args.get("presentation", "", type=str).strip() or None

    rows   = _visible_rows(module=module, presentation=presentation)
    buffer = generate_cohort_report_pdf(rows)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=_pdf_filename())
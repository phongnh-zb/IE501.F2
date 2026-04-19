import statistics

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from webapp.services.cache import SYSTEM_CACHE, get_model_results_from_hbase

features_bp = Blueprint("features", __name__)

# ── Feature metadata ──────────────────────────────────────────────────────────
FEATURES = [
    {"field": "clicks",            "label": "Total Clicks",      "short": "Clicks",     "group": "VLE Engagement"},
    {"field": "active_days",       "label": "Active Days",       "short": "Act.Days",   "group": "VLE Engagement"},
    {"field": "active_weeks",      "label": "Active Weeks",      "short": "Act.Wks",    "group": "VLE Engagement"},
    {"field": "engagement_ratio",  "label": "Engagement Ratio",  "short": "Eng.Ratio",  "group": "VLE Engagement"},
    {"field": "forum_clicks",      "label": "Forum Clicks",      "short": "Forum",      "group": "VLE Engagement"},
    {"field": "quiz_clicks",       "label": "Quiz Clicks",       "short": "Quiz",       "group": "VLE Engagement"},
    {"field": "resource_clicks",   "label": "Resource Clicks",   "short": "Resource",   "group": "VLE Engagement"},
    {"field": "score",             "label": "Avg Score",         "short": "Score",      "group": "Academic"},
    {"field": "weighted_score",    "label": "Weighted Score",    "short": "W.Score",    "group": "Academic"},
    {"field": "submission_rate",   "label": "Submission Rate",   "short": "Sub.Rate",   "group": "Academic"},
    {"field": "avg_days_early",    "label": "Avg Days Early",    "short": "Days.Early", "group": "Academic"},
    {"field": "exam_score",        "label": "Exam Score",        "short": "Exam",       "group": "Academic"},
    {"field": "tma_score",         "label": "TMA Score",         "short": "TMA",        "group": "Academic"},
    {"field": "cma_score",         "label": "CMA Score",         "short": "CMA",        "group": "Academic"},
    {"field": "withdrew_early",    "label": "Withdrew Early",    "short": "Withdrew",   "group": "Registration"},
    {"field": "days_before_start", "label": "Days Before Start", "short": "Reg.Days",   "group": "Registration"},
    {"field": "num_prev_attempts", "label": "Prev Attempts",     "short": "Prev.Att",   "group": "Demographics"},
    {"field": "imd_band_encoded",  "label": "IMD Band",          "short": "IMD",        "group": "Demographics"},
    {"field": "disability_encoded","label": "Disability",        "short": "Disability", "group": "Demographics"},
]

_FIELD_META   = {f["field"]: f for f in FEATURES}
_VALID_FIELDS = {f["field"] for f in FEATURES}

_MODEL_TO_CACHE = {
    "total_clicks":       "clicks",
    "active_days":        "active_days",
    "active_weeks":       "active_weeks",
    "engagement_ratio":   "engagement_ratio",
    "forum_clicks":       "forum_clicks",
    "quiz_clicks":        "quiz_clicks",
    "resource_clicks":    "resource_clicks",
    "avg_score":          "score",
    "weighted_avg_score": "weighted_score",
    "submission_rate":    "submission_rate",
    "avg_days_early":     "avg_days_early",
    "exam_score":         "exam_score",
    "tma_score":          "tma_score",
    "cma_score":          "cma_score",
    "withdrew_early":     "withdrew_early",
    "days_before_start":  "days_before_start",
    "num_prev_attempts":  "num_prev_attempts",
    "imd_band_encoded":   "imd_band_encoded",
    "disability_encoded": "disability_encoded",
}

_corr_cache = None


def _valid_val(v):
    return v is not None and v != "" and not (isinstance(v, float) and v != v)


def _percentile(sorted_vals, p):
    if not sorted_vals:
        return 0.0
    idx = (len(sorted_vals) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)


def _quartiles(values):
    if not values:
        return None
    s = sorted(v for v in values if _valid_val(v))
    if not s:
        return None
    return {
        "min":    round(_percentile(s, 1),  4),
        "q1":     round(_percentile(s, 25), 4),
        "median": round(_percentile(s, 50), 4),
        "q3":     round(_percentile(s, 75), 4),
        "max":    round(_percentile(s, 99), 4),
    }


def _pearson(xs, ys):
    paired = [(x, y) for x, y in zip(xs, ys) if _valid_val(x) and _valid_val(y)]
    n = len(paired)
    if n < 2:
        return 0.0
    mx = sum(p[0] for p in paired) / n
    my = sum(p[1] for p in paired) / n
    num = sum((p[0] - mx) * (p[1] - my) for p in paired)
    sx  = sum((p[0] - mx) ** 2 for p in paired) ** 0.5
    sy  = sum((p[1] - my) ** 2 for p in paired) ** 0.5
    if sx == 0 or sy == 0:
        return 0.0
    return round(num / (sx * sy), 3)


# ── Page route ────────────────────────────────────────────────────────────────

@features_bp.route("/features")
@login_required
def features():
    groups = {}
    for f in FEATURES:
        groups.setdefault(f["group"], []).append(f)
    return render_template(
        "features/index.html",
        feature_groups = groups,
        default_field  = "engagement_ratio",
    )


# ── API: histogram distribution ───────────────────────────────────────────────

@features_bp.route("/api/features/distribution")
@login_required
def features_distribution():
    field = request.args.get("feature", "engagement_ratio", type=str).strip()
    if field not in _VALID_FIELDS:
        return jsonify({"error": "Unknown feature"}), 400

    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"error": "Data not ready"}), 503

    data = SYSTEM_CACHE["data"]

    tier_vals = {0: [], 1: [], 2: [], 3: []}
    for row in data:
        v = row.get(field)
        if not _valid_val(v):
            continue
        if isinstance(v, (int, float)) and v < 0:
            continue
        tier = row.get("risk", 0)
        if tier in tier_vals:
            tier_vals[tier].append(float(v))

    all_vals = [v for vs in tier_vals.values() for v in vs]
    if not all_vals:
        return jsonify({"buckets": [], "safe": [], "watch": [], "high": [], "crit": []})

    all_sorted = sorted(all_vals)
    lo  = _percentile(all_sorted, 1)
    hi  = _percentile(all_sorted, 99)
    if lo == hi:
        hi = lo + 1

    n_buckets = 20
    width     = (hi - lo) / n_buckets
    labels    = []
    counts    = {0: [], 1: [], 2: [], 3: []}

    for i in range(n_buckets):
        bucket_lo = lo + i * width
        bucket_hi = lo + (i + 1) * width
        labels.append(f"{bucket_lo:.2f}–{bucket_hi:.2f}")
        for tier in [0, 1, 2, 3]:
            c = sum(1 for v in tier_vals[tier] if bucket_lo <= v < bucket_hi)
            counts[tier].append(c)

    for tier in [0, 1, 2, 3]:
        overflow = sum(1 for v in tier_vals[tier] if v >= hi)
        if overflow and counts[tier]:
            counts[tier][-1] += overflow

    return jsonify({
        "feature": field,
        "label":   _FIELD_META[field]["label"],
        "buckets": labels,
        "safe":    counts[0],
        "watch":   counts[1],
        "high":    counts[2],
        "crit":    counts[3],
    })


# ── API: box plot quartiles ───────────────────────────────────────────────────

@features_bp.route("/api/features/boxplot")
@login_required
def features_boxplot():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"error": "Data not ready"}), 503

    model_results = get_model_results_from_hbase()
    best = next((m for m in model_results if m.get("is_best")), model_results[0] if model_results else None)

    top_fields = []
    if best and best.get("importance"):
        ranked = sorted(best["importance"], key=lambda x: x.get("score", 0), reverse=True)
        for item in ranked:
            cache_field = _MODEL_TO_CACHE.get(item["feature"])
            if cache_field and cache_field in _VALID_FIELDS and cache_field not in top_fields:
                top_fields.append(cache_field)
            if len(top_fields) == 6:
                break

    if not top_fields:
        top_fields = [f["field"] for f in FEATURES[:6]]

    data   = SYSTEM_CACHE["data"]
    result = []
    for field in top_fields:
        tier_vals = {0: [], 1: [], 2: [], 3: []}
        for row in data:
            v = row.get(field)
            if not _valid_val(v) or (isinstance(v, (int, float)) and v < 0):
                continue
            tier = row.get("risk", 0)
            if tier in tier_vals:
                tier_vals[tier].append(float(v))

        tiers = {}
        for tier, vals in tier_vals.items():
            q = _quartiles(vals)
            if q:
                tiers[str(tier)] = q

        result.append({"field": field, "label": _FIELD_META[field]["label"], "tiers": tiers})

    return jsonify({"features": result})


# ── API: Pearson correlation matrix (upper triangle, null diagonal) ───────────

@features_bp.route("/api/features/correlation")
@login_required
def features_correlation():
    global _corr_cache

    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"error": "Data not ready"}), 503

    last_updated = SYSTEM_CACHE.get("last_updated")
    if _corr_cache and _corr_cache.get("last_updated") == last_updated:
        return jsonify(_corr_cache["data"])

    data   = SYSTEM_CACHE["data"]
    fields = [f["field"] for f in FEATURES]
    shorts = [f["short"] for f in FEATURES]

    vectors = {}
    for field in fields:
        vectors[field] = [
            float(row[field])
            for row in data
            if _valid_val(row.get(field))
            and not (isinstance(row.get(field), (int, float)) and row.get(field) < 0)
        ]

    n    = len(fields)
    rows = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                # Null diagonal — self-correlation adds no information
                row.append(None)
            elif j < i:
                # Null lower triangle — show upper triangle only
                row.append(None)
            else:
                row.append(_pearson(vectors[fields[i]], vectors[fields[j]]))
        rows.append(row)

    result = {
        "features": shorts,
        "labels":   [f["label"] for f in FEATURES],
        "matrix":   rows,
    }
    _corr_cache = {"last_updated": last_updated, "data": result}
    return jsonify(result)
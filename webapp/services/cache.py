import json
import logging
import math
import threading
import time

from common.hbase_client import SCAN_TIMEOUT, hbase_connection
from configs.config import CACHE_INTERVAL, MODEL_RESULTS_TABLE, TABLE_NAME

logger = logging.getLogger(__name__)

SYSTEM_CACHE = {
    "data": [],
    "last_updated": None,
    "is_ready": False,
}

RISK_LABELS = {0: "Safe", 1: "Watch", 2: "High Risk", 3: "Critical"}


def summarize_students_by_id(rows):
    worst = {}
    for x in rows:
        sid = x.get("id")
        if not sid:
            continue
        r = x.get("risk", 0)
        try:
            r = int(r)
        except (TypeError, ValueError):
            r = 0
        r = max(0, min(3, r))
        if sid not in worst or r > worst[sid]:
            worst[sid] = r

    safe = watch = high = critical = 0
    for r in worst.values():
        if r == 0:
            safe += 1
        elif r == 1:
            watch += 1
        elif r == 2:
            high += 1
        else:
            critical += 1

    return {
        "unique_students": len(worst),
        "safe":          safe,
        "watch":         watch,
        "high_risk":     high,
        "critical":      critical,
    }


def _safe_float(value_dict, key, default=0.0):
    raw = value_dict.get(key, str(default).encode())
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def _safe_int(value_dict, key, default=0):
    raw = value_dict.get(key, str(default).encode())
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return default


def fetch_all_data_from_hbase():
    data_buffer = []

    try:
        logger.info(">>> [CACHE] Starting data synchronization from HBase...")
        start_time = time.time()

        with hbase_connection(timeout=SCAN_TIMEOUT) as conn:
            table = conn.table(TABLE_NAME)
            for key, value in table.scan():
                try:
                    risk_tier = _safe_int(value, b"prediction:risk_tier")

                    # Row key is "{id_student}|{code_module}|{code_presentation}".
                    # Split to recover the plain student ID for display and search,
                    # while code_module and code_presentation are read from their
                    # HBase columns below (authoritative source).
                    student_id = key.decode("utf-8").split("|")[0]

                    data_buffer.append({
                        "id":                student_id,
                        "code_module":       value.get(b"info:code_module",       b"").decode("utf-8"),
                        "code_presentation": value.get(b"info:code_presentation", b"").decode("utf-8"),
                        "clicks":            _safe_float(value, b"info:total_clicks"),
                        "active_days":       _safe_int(value,   b"info:active_days"),
                        "active_weeks":      _safe_int(value,   b"info:active_weeks"),
                        "engagement_ratio":  _safe_float(value, b"info:engagement_ratio"),
                        "forum_clicks":      _safe_float(value, b"info:forum_clicks"),
                        "quiz_clicks":       _safe_float(value, b"info:quiz_clicks"),
                        "resource_clicks":   _safe_float(value, b"info:resource_clicks"),
                        "score":             _safe_float(value, b"info:avg_score"),
                        "weighted_score":    _safe_float(value, b"info:weighted_avg_score"),
                        "submission_rate":   _safe_float(value, b"info:submission_rate"),
                        "avg_days_early":    _safe_float(value, b"info:avg_days_early"),
                        "exam_score":        _safe_float(value, b"info:exam_score"),
                        "tma_score":         _safe_float(value, b"info:tma_score"),
                        "cma_score":         _safe_float(value, b"info:cma_score"),
                        "withdrew_early":    _safe_int(value,   b"info:withdrew_early"),
                        "num_prev_attempts": _safe_int(value,   b"info:num_prev_attempts"),
                        "imd_band_encoded":  _safe_int(value,   b"info:imd_band_encoded", -1),
                        "disability_encoded":_safe_int(value,   b"info:disability_encoded", -1),
                        "days_before_start": _safe_float(value, b"info:days_before_start"),
                        "gender":            value.get(b"info:gender",            b"").decode("utf-8"),
                        "region":            value.get(b"info:region",            b"").decode("utf-8"),
                        "highest_education": value.get(b"info:highest_education", b"").decode("utf-8"),
                        "imd_band":          value.get(b"info:imd_band",          b"").decode("utf-8"),
                        "age_band":          value.get(b"info:age_band",          b"").decode("utf-8"),
                        "studied_credits":   _safe_int(value,   b"info:studied_credits"),
                        "disability":        value.get(b"info:disability",        b"").decode("utf-8"),
                        "final_result":      value.get(b"info:final_result",      b"").decode("utf-8"),
                        "risk":              risk_tier,
                        "risk_label":        RISK_LABELS.get(risk_tier, "Unknown"),
                    })
                except Exception:
                    continue

        SYSTEM_CACHE["data"] = data_buffer
        SYSTEM_CACHE["last_updated"] = time.strftime("%H:%M:%S %Y/%m/%d")
        SYSTEM_CACHE["is_ready"] = True

        duration = time.time() - start_time
        logger.info(
            f">>> [CACHE] Synchronization complete. "
            f"Loaded {len(data_buffer)} records in {duration:.2f}s."
        )

    except Exception as e:
        logger.error(f">>> [CACHE] Sync Error: {e}")


def background_scheduler():
    while True:
        fetch_all_data_from_hbase()
        logger.info(f">>> [SCHEDULER] Sleeping for {CACHE_INTERVAL}s...")
        time.sleep(CACHE_INTERVAL)


def start_background_scheduler():
    t = threading.Thread(target=background_scheduler, daemon=True)
    t.start()


def get_filter_options(modules=None):
    data = SYSTEM_CACHE.get("data", [])
    if modules:
        data = [x for x in data if x.get("code_module", "") in modules]
    mods = sorted({x["code_module"]       for x in data if x.get("code_module")})
    pres = sorted({x["code_presentation"] for x in data if x.get("code_presentation")})
    return {"modules": mods, "presentations": pres}


def get_data_from_memory(
    page=1, page_size=50, search_query="",
    sort_by="risk", order="desc", modules=None,
    risk_filter=None, module_filter=None,
    presentation_filter=None, withdrew_filter=None,
):
    if not SYSTEM_CACHE["is_ready"]:
        return {"data": [], "total_pages": 0, "total_records": 0,
                "page": 1, "tier_counts": {}}

    all_data = SYSTEM_CACHE["data"]

    if modules:
        all_data = [x for x in all_data if x.get("code_module", "") in modules]

    if module_filter:
        all_data = [x for x in all_data if x.get("code_module", "") == module_filter]

    if risk_filter:
        all_data = [x for x in all_data if x["risk"] in risk_filter]

    if presentation_filter:
        all_data = [x for x in all_data if x.get("code_presentation") == presentation_filter]

    if withdrew_filter is not None:
        all_data = [x for x in all_data if x["withdrew_early"] == withdrew_filter]

    if search_query:
        q = search_query.lower()
        filtered_data = [x for x in all_data if q in x["id"].lower()]
    else:
        filtered_data = list(all_data)

    agg = summarize_students_by_id(filtered_data)
    tier_counts = {
        "safe":     agg["safe"],
        "watch":    agg["watch"],
        "high":     agg["high_risk"],
        "critical": agg["critical"],
    }

    reverse = order == "desc"
    try:
        if sort_by == "risk":
            filtered_data.sort(
                key=lambda x: (x["risk"], -x["score"]),
                reverse=reverse,
            )
        else:
            filtered_data.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
    except Exception as e:
        logger.error(f"Sort Error: {e}")

    total_records = len(filtered_data)
    total_pages   = math.ceil(total_records / page_size) if total_records > 0 else 1
    page          = max(1, min(page, total_pages))
    start         = (page - 1) * page_size

    return {
        "data":          filtered_data[start: start + page_size],
        "page":          page,
        "total_pages":   total_pages,
        "total_records": total_records,
        "tier_counts":   tier_counts,
    }


def get_student_by_id(student_id, code_module=None, code_presentation=None):
    if not SYSTEM_CACHE["is_ready"]:
        return None
    for st in SYSTEM_CACHE["data"]:
        if st["id"] != student_id:
            continue
        if code_module and st.get("code_module") != code_module:
            continue
        if code_presentation and st.get("code_presentation") != code_presentation:
            continue
        return st
    return None


def _parse_model_row(key, value):
    raw_key = key.decode("utf-8")
    if "|" in raw_key:
        model_key, run_id = raw_key.rsplit("|", 1)
    else:
        model_key, run_id = raw_key, "00000000_000000"
    return {
        "name":           model_key.replace("_", " "),
        "run_id":         run_id,
        "auc":            _safe_float(value, b"metrics:auc"),
        "accuracy":       _safe_float(value, b"metrics:accuracy"),
        "precision":      _safe_float(value, b"metrics:precision"),
        "recall":         _safe_float(value, b"metrics:recall"),
        "f1":             _safe_float(value, b"metrics:f1"),
        "cv_auc":         _safe_float(value, b"metrics:cv_auc"),
        "composite_score":_safe_float(value, b"metrics:composite_score"),
        "training_time":  _safe_float(value, b"metrics:training_time"),
        "is_best":        value.get(b"info:is_best", b"false").decode() == "true",
        "timestamp":      value.get(b"info:timestamp", b"").decode(),
        "importance":     json.loads(value.get(b"importance:json", b"[]").decode()),
        "tuning":         json.loads(value.get(b"tuning:json", b"{}").decode()),
    }


def get_model_results_from_hbase():
    all_rows = []
    try:
        with hbase_connection() as conn:
            table = conn.table(MODEL_RESULTS_TABLE)
            for key, value in table.scan():
                all_rows.append(_parse_model_row(key, value))
    except Exception as e:
        logger.error(f">>> [CACHE] Model results fetch error: {e}")
        return []

    latest = {}
    for row in all_rows:
        name = row["name"]
        if name not in latest or row["run_id"] > latest[name]["run_id"]:
            latest[name] = row

    return sorted(latest.values(), key=lambda x: x.get("composite_score", x["auc"]), reverse=True)


def get_model_history_from_hbase():
    all_rows = []
    try:
        with hbase_connection() as conn:
            table = conn.table(MODEL_RESULTS_TABLE)
            for key, value in table.scan():
                row = _parse_model_row(key, value)
                row.pop("importance", None)
                row.pop("tuning", None)
                all_rows.append(row)
    except Exception as e:
        logger.error(f">>> [CACHE] Model history fetch error: {e}")
        return {}

    history = {}
    for row in all_rows:
        history.setdefault(row["name"], []).append(row)

    for runs in history.values():
        runs.sort(key=lambda x: x["run_id"])

    return history
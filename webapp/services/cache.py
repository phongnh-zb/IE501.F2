import json
import logging
import math
import threading
import time

from configs.config import TABLE_NAME, MODEL_RESULTS_TABLE, CACHE_INTERVAL
from src.storage.hbase_client import SCAN_TIMEOUT, hbase_connection

logger = logging.getLogger(__name__)

SYSTEM_CACHE = {
    "data": [],
    "last_updated": None,
    "is_ready": False,
}

RISK_LABELS = {0: "Safe", 1: "Watch", 2: "High Risk", 3: "Critical"}


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
                    data_buffer.append({
                        "id":                key.decode("utf-8"),
                        "clicks":            _safe_float(value, b"info:total_clicks"),
                        "active_days":       _safe_int(value,   b"info:active_days"),
                        "forum_clicks":      _safe_float(value, b"info:forum_clicks"),
                        "quiz_clicks":       _safe_float(value, b"info:quiz_clicks"),
                        "resource_clicks":   _safe_float(value, b"info:resource_clicks"),
                        "score":             _safe_float(value, b"info:avg_score"),
                        "weighted_score":    _safe_float(value, b"info:weighted_avg_score"),
                        "submission_rate":   _safe_float(value, b"info:submission_rate"),
                        "avg_days_early":    _safe_float(value, b"info:avg_days_early"),
                        "withdrew_early":    _safe_int(value,   b"info:withdrew_early"),
                        "num_prev_attempts": _safe_int(value,   b"info:num_prev_attempts"),
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


def get_data_from_memory(page=1, page_size=50, search_query="", sort_by="id", order="asc"):
    if not SYSTEM_CACHE["is_ready"]:
        return {"data": [], "total_pages": 0, "total_records": 0, "page": 1}

    all_data = SYSTEM_CACHE["data"]

    if search_query:
        q = search_query.lower()
        filtered_data = [x for x in all_data if q in x["id"].lower()]
    else:
        filtered_data = list(all_data)

    reverse = order == "desc"
    try:
        filtered_data.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
    except Exception as e:
        logger.error(f"Sort Error: {e}")

    total_records = len(filtered_data)
    total_pages   = math.ceil(total_records / page_size) if total_records > 0 else 1

    page  = max(1, min(page, total_pages))
    start = (page - 1) * page_size

    return {
        "data":          filtered_data[start: start + page_size],
        "page":          page,
        "total_pages":   total_pages,
        "total_records": total_records,
    }


def get_student_by_id(student_id):
    if not SYSTEM_CACHE["is_ready"]:
        return None
    for st in SYSTEM_CACHE["data"]:
        if st["id"] == student_id:
            return st
    return None


def _parse_model_row(key, value):
    raw_key = key.decode("utf-8")
    if "|" in raw_key:
        model_key, run_id = raw_key.rsplit("|", 1)
    else:
        model_key, run_id = raw_key, "00000000_000000"
    return {
        "name":          model_key.replace("_", " "),
        "run_id":        run_id,
        "auc":           _safe_float(value, b"metrics:auc"),
        "accuracy":      _safe_float(value, b"metrics:accuracy"),
        "precision":     _safe_float(value, b"metrics:precision"),
        "recall":        _safe_float(value, b"metrics:recall"),
        "f1":            _safe_float(value, b"metrics:f1"),
        "cv_auc":        _safe_float(value, b"metrics:cv_auc"),
        "training_time": _safe_float(value, b"metrics:training_time"),
        "is_best":       value.get(b"info:is_best", b"false").decode() == "true",
        "timestamp":     value.get(b"info:timestamp", b"").decode(),
        "importance":    json.loads(value.get(b"importance:json", b"[]").decode()),
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

    return sorted(latest.values(), key=lambda x: x["auc"], reverse=True)


def get_model_history_from_hbase():
    all_rows = []
    try:
        with hbase_connection() as conn:
            table = conn.table(MODEL_RESULTS_TABLE)
            for key, value in table.scan():
                row = _parse_model_row(key, value)
                row.pop("importance", None)
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
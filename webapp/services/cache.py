import logging
import math
import threading
import time

import happybase

from configs.config import HBASE_HOST, HBASE_PORT, TABLE_NAME, CACHE_INTERVAL

logger = logging.getLogger(__name__)

SYSTEM_CACHE = {
    "data": [],
    "last_updated": None,
    "is_ready": False,
}


def fetch_all_data_from_hbase():
    connection = None
    data_buffer = []

    try:
        logger.info(">>> [CACHE] Starting data synchronization from HBase...")
        start_time = time.time()

        connection = happybase.Connection(host=HBASE_HOST, port=HBASE_PORT, timeout=60000)
        connection.open()
        table = connection.table(TABLE_NAME)

        for key, value in table.scan():
            try:
                data_buffer.append({
                    "id": key.decode("utf-8"),
                    "clicks": float(value.get(b"info:clicks", b"0")),
                    "score": float(value.get(b"info:avg_score", b"0")),
                    "risk": int(value.get(b"prediction:risk_label", b"0")),
                })
            except Exception:
                continue

        SYSTEM_CACHE["data"] = data_buffer
        SYSTEM_CACHE["last_updated"] = time.strftime("%H:%M:%S")
        SYSTEM_CACHE["is_ready"] = True

        duration = time.time() - start_time
        logger.info(
            f">>> [CACHE] ✅ Synchronization complete. "
            f"Loaded {len(data_buffer)} records in {duration:.2f}s."
        )

    except Exception as e:
        logger.error(f">>> [CACHE] ❌ Sync Error: {e}")
    finally:
        if connection:
            connection.close()


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
    total_pages = math.ceil(total_records / page_size) if total_records > 0 else 1

    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "data": filtered_data[start:end],
        "page": page,
        "total_pages": total_pages,
        "total_records": total_records,
    }


def get_student_by_id(student_id):
    if not SYSTEM_CACHE["is_ready"]:
        return None
    for st in SYSTEM_CACHE["data"]:
        if st["id"] == student_id:
            return st
    return None
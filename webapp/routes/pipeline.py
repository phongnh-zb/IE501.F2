import re
import socket

from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from configs.config import (FLASK_PORT, HADOOP_HOST, HBASE_HOST, HBASE_PORT,
                            HDFS_BASE_PATH, HDFS_OUTPUT_PATH,
                            MODEL_RESULTS_TABLE, TABLE_NAME)
from webapp.auth.decorators import admin_required
from webapp.services.cache import SYSTEM_CACHE, summarize_students_by_id

pipeline_bp = Blueprint("pipeline", __name__)

# Well-known ports for each service — all checked via TCP so Docker works
_SVC_PORTS = {
    "namenode":        [(HADOOP_HOST, 9000), (HADOOP_HOST, 9870)],
    "datanode":        [(HADOOP_HOST, 9864)],
    "resourcemanager": [(HADOOP_HOST, 8088)],
    "hmaster":         [(HBASE_HOST,  16010), (HBASE_HOST, 16000)],
    "thrift":          [(HBASE_HOST,  HBASE_PORT)],
    "flask":           [("localhost",  FLASK_PORT)],
}


def _port_open(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _service_up(key):
    return any(_port_open(h, p) for h, p in _SVC_PORTS[key])


def _hdfs_ls(path):
    # Use WebHDFS REST API — works from Docker and directly
    import json
    import urllib.request
    hdfs_path = re.sub(r"^hdfs://[^/]+", "", path).rstrip("/")
    url = f"http://{HADOOP_HOST}:9870/webhdfs/v1{hdfs_path}?op=LISTSTATUS"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data     = json.loads(r.read())
            statuses = data.get("FileStatuses", {}).get("FileStatus", [])
            return {"exists": True, "count": len(statuses)}
    except Exception:
        return {"exists": False, "count": 0}


def _hbase_row_count(table_name, column):
    try:
        from common.hbase_client import hbase_connection
        with hbase_connection() as conn:
            table = conn.table(table_name)
            return sum(1 for _ in table.scan(columns=[column]))
    except Exception:
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@pipeline_bp.route("/pipeline")
@login_required
@admin_required
def pipeline():
    return render_template("pipeline/index.html")


@pipeline_bp.route("/api/pipeline/status")
@login_required
@admin_required
def pipeline_status():
    services = [
        {
            "name":   "NameNode",
            "group":  "Hadoop",
            "up":     _service_up("namenode"),
            "detail": "ports 9000 / 9870",
            "web_ui": "http://localhost:9870",
        },
        {
            "name":   "DataNode",
            "group":  "Hadoop",
            "up":     _service_up("datanode"),
            "detail": "port 9864",
            "web_ui": "http://localhost:9864",
        },
        {
            "name":   "ResourceManager",
            "group":  "Hadoop",
            "up":     _service_up("resourcemanager"),
            "detail": "port 8088",
            "web_ui": "http://localhost:8088",
        },
        {
            "name":   "HMaster",
            "group":  "HBase",
            "up":     _service_up("hmaster"),
            "detail": "port 16010",
            "web_ui": "http://localhost:16010",
        },
        {
            "name":   "Thrift Server",
            "group":  "HBase",
            "up":     _service_up("thrift"),
            "detail": f"port {HBASE_PORT} · binary RPC",
            "web_ui": None,
        },
        {
            "name":   "Flask Dashboard",
            "group":  "App",
            "up":     _service_up("flask"),
            "detail": f"port {FLASK_PORT}",
            "web_ui": None,
        },
    ]

    all_up   = sum(1 for s in services if s["up"])
    all_down = len(services) - all_up

    cache_rows = SYSTEM_CACHE.get("data", [])
    cache_agg  = summarize_students_by_id(cache_rows)

    hdfs_raw  = _hdfs_ls(HDFS_BASE_PATH)
    hdfs_proc = _hdfs_ls(HDFS_OUTPUT_PATH)

    hmaster_up        = _service_up("hmaster")
    predictions_count = _hbase_row_count(TABLE_NAME,          b"prediction:risk_tier") if hmaster_up else None
    models_count      = _hbase_row_count(MODEL_RESULTS_TABLE, b"info:timestamp")        if hmaster_up else None

    return jsonify({
        "services": services,
        "summary":  {"up": all_up, "down": all_down, "total": len(services)},
        "data": {
            "hdfs_raw":    {**hdfs_raw,  "path": HDFS_BASE_PATH},
            "hdfs_proc":   {**hdfs_proc, "path": HDFS_OUTPUT_PATH},
            "predictions": predictions_count,
            "models":      models_count,
        },
        "cache": {
            "is_ready":      SYSTEM_CACHE["is_ready"],
            "last_updated":  SYSTEM_CACHE["last_updated"],
            "student_count": cache_agg["unique_students"],
        },
    })
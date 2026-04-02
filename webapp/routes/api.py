import logging

from flask import Blueprint, jsonify

from webapp.services.cache import (
    SYSTEM_CACHE,
    fetch_all_data_from_hbase,
    get_student_by_id,
)
from webapp.services.recommendations import generate_smart_recommendations

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/realtime-data")
def realtime_data():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"raw_data": [], "summary": {"total": 0, "risk": 0, "safe": 0}})

    data_sample = SYSTEM_CACHE["data"]
    total = len(data_sample)
    risk = sum(1 for x in data_sample if x["risk"] == 1)
    safe = total - risk

    return jsonify({
        "raw_data": data_sample,
        "summary": {
            "total": total,
            "risk": risk,
            "safe": safe,
            "last_updated": SYSTEM_CACHE["last_updated"],
        },
    })


@api_bp.route("/student/<student_id>")
def student_detail(student_id):
    student = get_student_by_id(student_id)

    if not student:
        return jsonify({"error": "Not found"}), 404

    recommendations = generate_smart_recommendations(student)

    return jsonify({"info": student, "recommendations": recommendations})


@api_bp.route("/refresh-cache", methods=["POST"])
def refresh_cache():
    try:
        fetch_all_data_from_hbase()
        return jsonify({
            "status": "success",
            "message": "Cache updated successfully",
            "last_updated": SYSTEM_CACHE["last_updated"],
        })
    except Exception as e:
        logger.error(f"Manual Refresh Failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
import logging

from flask import Blueprint, jsonify, send_file

from webapp.services.cache import (SYSTEM_CACHE, fetch_all_data_from_hbase,
                                   get_student_by_id)
from webapp.services.pdf_export import (generate_cohort_report_pdf,
                                        generate_student_report_pdf)
from webapp.services.recommendations import generate_smart_recommendations

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/realtime-data")
def realtime_data():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({
            "raw_data": [],
            "summary": {"total": 0, "safe": 0, "watch": 0, "high_risk": 0, "critical": 0},
        })

    data = SYSTEM_CACHE["data"]
    total    = len(data)
    safe     = sum(1 for x in data if x["risk"] == 0)
    watch    = sum(1 for x in data if x["risk"] == 1)
    high     = sum(1 for x in data if x["risk"] == 2)
    critical = sum(1 for x in data if x["risk"] == 3)

    return jsonify({
        "raw_data": data,
        "summary": {
            "total":    total,
            "safe":     safe,
            "watch":    watch,
            "high_risk": high,
            "critical": critical,
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


@api_bp.route("/student/<student_id>/report")
def student_report(student_id):
    student = get_student_by_id(student_id)
    if not student:
        return jsonify({"error": "Not found"}), 404

    recommendations = generate_smart_recommendations(student)
    buffer = generate_student_report_pdf(student, recommendations)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"student_{student_id}_report.pdf",
    )


@api_bp.route("/cohort/report")
def cohort_report():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"error": "Data not ready — run the pipeline first"}), 503

    buffer = generate_cohort_report_pdf(SYSTEM_CACHE["data"])

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="cohort_risk_report.pdf",
    )


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
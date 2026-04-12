import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from flask_login import current_user, login_required

from webapp.services.cache import (SYSTEM_CACHE, fetch_all_data_from_hbase,
                                   get_student_by_id, summarize_students_by_id)
from webapp.services.pdf_export import (generate_cohort_report_pdf,
                                        generate_student_report_pdf)
from webapp.services.recommendations import generate_smart_recommendations

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _visible_data():
    data = SYSTEM_CACHE["data"]
    if current_user.is_admin or not current_user.modules:
        return data
    return [s for s in data if s.get("code_module", "") in current_user.modules]


def pdf_filename(prefix="student_0_report"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.pdf"


@api_bp.route("/students")
@login_required
def students_data():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"students": [], "last_updated": None, "is_ready": False})
    return jsonify({
        "students":     _visible_data(),
        "last_updated": SYSTEM_CACHE["last_updated"],
        "is_ready":     True,
    })


@api_bp.route("/realtime-data")
@login_required
def realtime_data():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({
            "raw_data": [],
            "summary": {"total": 0, "safe": 0, "watch": 0, "high_risk": 0, "critical": 0},
        })

    data = _visible_data()
    agg  = summarize_students_by_id(data)

    return jsonify({
        "raw_data": data,
        "summary": {
            "total":         agg["unique_students"],
            "safe":          agg["safe"],
            "watch":         agg["watch"],
            "high_risk":     agg["high_risk"],
            "critical":      agg["critical"],
            "last_updated":  SYSTEM_CACHE["last_updated"],
        },
    })


@api_bp.route("/student/<student_id>")
@login_required
def student_detail(student_id):
    module       = request.args.get("module",       "", type=str).strip() or None
    presentation = request.args.get("presentation", "", type=str).strip() or None

    student = get_student_by_id(student_id, code_module=module, code_presentation=presentation)
    if not student:
        return jsonify({"error": "Not found"}), 404

    if not current_user.can_see_module(student.get("code_module", "")):
        return jsonify({"error": "Access denied"}), 403

    recommendations = generate_smart_recommendations(student)
    return jsonify({"info": student, "recommendations": recommendations})


@api_bp.route("/student/<student_id>/report")
@login_required
def student_report(student_id):
    module       = request.args.get("module",       "", type=str).strip() or None
    presentation = request.args.get("presentation", "", type=str).strip() or None

    student = get_student_by_id(student_id, code_module=module, code_presentation=presentation)
    if not student:
        return jsonify({"error": "Not found"}), 404

    if not current_user.can_see_module(student.get("code_module", "")):
        return jsonify({"error": "Access denied"}), 403

    recommendations = generate_smart_recommendations(student)
    buffer = generate_student_report_pdf(student, recommendations)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=pdf_filename(prefix=f"student_{student_id}_report"))


@api_bp.route("/cohort/report")
@login_required
def cohort_report():
    if not SYSTEM_CACHE["is_ready"]:
        return jsonify({"error": "Data not ready — run the pipeline first"}), 503

    buffer = generate_cohort_report_pdf(_visible_data())
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name="cohort_risk_report.pdf")


@api_bp.route("/refresh-cache", methods=["POST"])
@login_required
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
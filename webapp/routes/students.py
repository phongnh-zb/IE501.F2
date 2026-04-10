from datetime import datetime

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from webapp.services.cache import (SYSTEM_CACHE, get_data_from_memory,
                                   get_filter_options)
from webapp.services.csv_export import csv_filename, generate_students_csv

students_bp = Blueprint("students", __name__)

VALID_SORT   = {"id", "code_module", "score", "submission_rate", "active_days",
                "clicks", "risk", "withdrew_early"}
VALID_ORDER  = {"asc", "desc"}
VALID_SIZES  = {25, 50, 100}


@students_bp.route("/students")
@login_required
def students():
    if not SYSTEM_CACHE["is_ready"]:
        return render_template("partials/loading.html")

    modules        = None if current_user.is_admin else current_user.modules
    filter_options = get_filter_options(modules=modules)

    return render_template(
        "students/index.html",
        modules_available       = filter_options["modules"],
        presentations_available = filter_options["presentations"],
        last_updated            = SYSTEM_CACHE["last_updated"],
    )


@students_bp.route("/students/export")
@login_required
def export_students():
    if not SYSTEM_CACHE["is_ready"]:
        return Response("Data not ready.", status=503, mimetype="text/plain")

    # Parse filters from URL params to allow exporting the current view
    _TIER_NAMES = {"3": "Critical", "2": "High Risk", "1": "Watch", "0": "Safe"}
    modules      = None if current_user.is_admin else current_user.modules
    search       = request.args.get("search",       "", type=str).strip()
    risk_raw     = request.args.get("risk",         "", type=str).strip()
    module_f     = request.args.get("module",       "", type=str).strip() or None
    presentation = request.args.get("presentation", "", type=str).strip() or None
    withdrew_raw = request.args.get("withdrew",     "", type=str)
    sort_by      = request.args.get("sort_by",      "risk")
    order        = request.args.get("order",        "desc")

    valid_tiers      = {"0", "1", "2", "3"}
    risk_filter      = {int(r) for r in risk_raw.split(",") if r in valid_tiers} or None
    withdrew_filter  = int(withdrew_raw) if withdrew_raw in {"0", "1"} else None
    if sort_by not in VALID_SORT: sort_by = "risk"
    if order not in VALID_ORDER:  order   = "desc"

    result = get_data_from_memory(
        page=1, page_size=999_999,
        search_query=search, sort_by=sort_by, order=order,
        modules=modules, risk_filter=risk_filter,
        module_filter=module_f,
        presentation_filter=presentation,
        withdrew_filter=withdrew_filter,
    )

    return Response(
        generate_students_csv(result["data"]),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={csv_filename()}",
            "X-Accel-Buffering":   "no",
        },
    )
from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from webapp.services.cache import (SYSTEM_CACHE, get_data_from_memory,
                                   get_filter_options)
from webapp.services.csv_export import csv_filename, generate_students_csv

students_bp = Blueprint("students", __name__)

VALID_SORT  = {"id", "score", "submission_rate", "active_days", "clicks", "risk"}
VALID_ORDER = {"asc", "desc"}
VALID_SIZES = {25, 50, 100}


def _page_range(current, total):
    if total <= 7:
        return list(range(1, total + 1))
    pages = [1]
    if current > 3:
        pages.append(None)
    for p in range(max(2, current - 1), min(total, current + 2)):
        pages.append(p)
    if current < total - 2:
        pages.append(None)
    if total not in pages:
        pages.append(total)
    return pages


def _parse_filters():
    """Extract and validate all filter params from request.args."""
    sort_by      = request.args.get("sort_by",      "risk")
    order        = request.args.get("order",        "desc")
    risk_raw     = request.args.get("risk",         "", type=str)
    presentation = request.args.get("presentation", "", type=str).strip()
    withdrew_raw = request.args.get("withdrew",     "", type=str)

    risk_raw     = request.args.get("risk", "", type=str).strip()

    if sort_by not in VALID_SORT:
        sort_by = "risk"
    if order not in VALID_ORDER:
        order = "desc"

    # risk_raw is comma-separated, e.g. "2,3" for High+Critical
    valid_tiers  = {"0", "1", "2", "3"}
    risk_set     = {int(r) for r in risk_raw.split(",") if r in valid_tiers}

    return {
        "search":        request.args.get("search", "", type=str).strip(),
        "sort_by":       sort_by,
        "order":         order,
        "risk_raw":      risk_raw,
        "module":        request.args.get("module", "", type=str).strip(),
        "presentation":  presentation,
        "withdrew_raw":  withdrew_raw,
        "risk_filter":   risk_set if risk_set else None,
        "withdrew_filter": int(withdrew_raw) if withdrew_raw in {"0","1"} else None,
    }


@students_bp.route("/students")
@login_required
def students():
    if not SYSTEM_CACHE["is_ready"]:
        return render_template("partials/loading.html")

    page      = max(1, request.args.get("page",      1,  type=int))
    page_size = request.args.get("page_size", 50, type=int)
    if page_size not in VALID_SIZES:
        page_size = 50

    f = _parse_filters()
    modules = None if current_user.is_admin else current_user.modules

    result = get_data_from_memory(
        page=page, page_size=page_size,
        search_query=f["search"], sort_by=f["sort_by"], order=f["order"],
        modules=modules, risk_filter=f["risk_filter"],
        module_filter=f["module"] or None,
        presentation_filter=f["presentation"] or None,
        withdrew_filter=f["withdrew_filter"],
    )

    filter_options = get_filter_options(modules=modules)

    _TIER_NAMES = {"3": "Critical", "2": "High Risk", "1": "Watch", "0": "Safe"}
    _selected   = [r for r in f["risk_raw"].split(",") if r in _TIER_NAMES]
    if len(_selected) == 0:
        risk_label = ""
    elif len(_selected) == 1:
        risk_label = _TIER_NAMES[_selected[0]]
    else:
        risk_label = f"{len(_selected)} tiers selected"

    return render_template(
        "students/index.html",
        students                = result["data"],
        page                    = result["page"],
        total_pages             = result["total_pages"],
        total_records           = result["total_records"],
        tier_counts             = result["tier_counts"],
        page_range              = _page_range(result["page"], result["total_pages"]),
        page_size               = page_size,
        search                  = f["search"],
        sort_by                 = f["sort_by"],
        order                   = f["order"],
        risk_filter             = f["risk_raw"],
        risk_label              = risk_label,
        module_filter           = f["module"],
        presentation            = f["presentation"],
        withdrew                = f["withdrew_raw"],
        modules_available       = filter_options["modules"],
        presentations_available = filter_options["presentations"],
        last_updated            = SYSTEM_CACHE["last_updated"],
    )


@students_bp.route("/students/export")
@login_required
def export_students():
    """Stream the full filtered result set as a CSV download."""
    if not SYSTEM_CACHE["is_ready"]:
        return Response("Data not ready — run the pipeline first.", status=503,
                        mimetype="text/plain")

    f = _parse_filters()
    modules = None if current_user.is_admin else current_user.modules

    # page_size=0 sentinel — get_data_from_memory returns all rows when
    # page_size is very large; use total_records after first call
    result = get_data_from_memory(
        page=1, page_size=999_999,
        search_query=f["search"], sort_by=f["sort_by"], order=f["order"],
        modules=modules, risk_filter=f["risk_filter"],
        module_filter=f["module"] or None,
        presentation_filter=f["presentation"] or None,
        withdrew_filter=f["withdrew_filter"],
    )

    rows = result["data"]

    return Response(
        generate_students_csv(rows),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={csv_filename()}",
            "X-Accel-Buffering":   "no",
        },
    )
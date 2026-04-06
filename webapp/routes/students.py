from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from webapp.services.cache import SYSTEM_CACHE, get_data_from_memory

students_bp = Blueprint("students", __name__)


@students_bp.route("/students")
@login_required
def students():
    if not SYSTEM_CACHE["is_ready"]:
        return render_template("partials/loading.html")

    page      = request.args.get("page",      1,    type=int)
    page_size = request.args.get("page_size", 50,   type=int)
    search    = request.args.get("search",    "",   type=str)
    sort_by   = request.args.get("sort_by",   "id", type=str)
    order     = request.args.get("order",     "asc",type=str)

    # Lecturers are filtered to their assigned modules
    modules = None if current_user.is_admin else current_user.modules

    result = get_data_from_memory(page, page_size, search, sort_by, order, modules=modules)

    return render_template(
        "students.html",
        students=result["data"],
        page=result["page"],
        total_pages=result["total_pages"],
        total_records=result["total_records"],
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        order=order,
        last_updated=SYSTEM_CACHE["last_updated"],
        user_role=current_user.role,
    )
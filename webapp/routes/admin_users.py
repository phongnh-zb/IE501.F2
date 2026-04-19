import re

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from webapp.auth.db import (create_user, delete_user, get_user_by_username,
                            list_users, update_password,
                            update_user_role_modules)
from webapp.auth.decorators import admin_required
from webapp.services.cache import get_filter_options

admin_users_bp = Blueprint("admin_users", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _available_modules():
    return get_filter_options()["modules"]


# ── Page ──────────────────────────────────────────────────────────────────────

@admin_users_bp.route("/admin/users")
@login_required
@admin_required
def users():
    return render_template(
        "admin/users/index.html",
        users            = list_users(),
        modules_available = _available_modules(),
    )


# ── Create lecturer ───────────────────────────────────────────────────────────

@admin_users_bp.route("/admin/users/create", methods=["POST"])
@login_required
@admin_required
def create():
    username   = request.form.get("username",         "").strip()
    full_name  = request.form.get("full_name",        "").strip()
    email      = request.form.get("email",            "").strip()
    password   = request.form.get("password",         "")
    confirm    = request.form.get("confirm_password", "")
    modules    = request.form.getlist("modules")

    if not username:
        flash("Username is required.", "error")
        return redirect(url_for("admin_users.users"))
    if not full_name:
        flash("Full name is required.", "error")
        return redirect(url_for("admin_users.users"))
    if not email or not _EMAIL_RE.match(email):
        flash("A valid email address is required.", "error")
        return redirect(url_for("admin_users.users"))
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin_users.users"))
    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("admin_users.users"))

    existing, _ = get_user_by_username(username)
    if existing:
        flash(f"Username '{username}' is already taken.", "error")
        return redirect(url_for("admin_users.users"))

    try:
        create_user(
            username      = username,
            password_hash = generate_password_hash(password),
            role          = "lecturer",
            modules       = modules,
            full_name     = full_name,
            email         = email,
            created_by    = current_user.username,
        )
        flash(f"Lecturer '{full_name}' created successfully.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("admin_users.users"))


# ── Edit lecturer ─────────────────────────────────────────────────────────────

@admin_users_bp.route("/admin/users/<int:user_id>/edit", methods=["POST"])
@login_required
@admin_required
def edit(user_id):
    full_name = request.form.get("full_name", "").strip()
    email     = request.form.get("email",     "").strip()
    modules   = request.form.getlist("modules")

    if not full_name:
        flash("Full name is required.", "error")
        return redirect(url_for("admin_users.users"))
    if not email or not _EMAIL_RE.match(email):
        flash("A valid email address is required.", "error")
        return redirect(url_for("admin_users.users"))

    try:
        update_user_role_modules(user_id, full_name, email, modules,
                                 updated_by=current_user.username)
        flash("User updated successfully.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("admin_users.users"))


# ── Reset password ────────────────────────────────────────────────────────────

@admin_users_bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    password = request.form.get("password",         "")
    confirm  = request.form.get("confirm_password", "")

    if len(password) < 8:
        flash("Password must be at least 8 characters.", "error")
        return redirect(url_for("admin_users.users"))
    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("admin_users.users"))

    update_password(user_id, generate_password_hash(password))
    flash("Password reset successfully.", "success")
    return redirect(url_for("admin_users.users"))


# ── Delete ────────────────────────────────────────────────────────────────────

@admin_users_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(user_id):
    try:
        delete_user(user_id, requesting_user_id=current_user.id)
        flash("User deleted.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin_users.users"))
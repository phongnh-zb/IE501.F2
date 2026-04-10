import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from webapp.auth.db import (get_user_by_id, get_user_by_username,
                            update_password, update_user_info)

profile_bp = Blueprint("profile", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@profile_bp.route("/profile")
@login_required
def profile():
    user = get_user_by_id(current_user.id)
    return render_template("profile/index.html", user=user)


@profile_bp.route("/profile/info", methods=["POST"])
@login_required
def update_info():
    full_name = request.form.get("full_name", "").strip()
    email     = request.form.get("email", "").strip()

    if not full_name:
        flash("Full name is required.", "error")
        return redirect(url_for("profile.profile"))

    if not email or not _EMAIL_RE.match(email):
        flash("A valid email address is required.", "error")
        return redirect(url_for("profile.profile"))

    try:
        update_user_info(current_user.id, full_name, email)
        # Reflect changes in the live session object
        current_user.full_name = full_name
        current_user.email     = email
        flash("Profile updated successfully.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("profile.profile"))


@profile_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    current_pw  = request.form.get("current_password", "")
    new_pw      = request.form.get("new_password", "")
    confirm_pw  = request.form.get("confirm_password", "")

    _, stored_hash = get_user_by_username(current_user.username)

    if not check_password_hash(stored_hash, current_pw):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile.profile"))

    if len(new_pw) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("profile.profile"))

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile.profile"))

    update_password(current_user.id, generate_password_hash(new_pw))

    logout_user()
    flash("Password changed successfully. Please sign in with your new password.", "success")
    return redirect(url_for("auth.login"))
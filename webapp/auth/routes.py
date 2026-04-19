from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from webapp.auth.db import (get_user_by_username, increment_failed_attempts,
                            update_last_login)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user, password_hash = get_user_by_username(username)

        # Check block status first — before password verification
        if user and user.is_blocked:
            flash(
                "Your account is blocked. Please contact an administrator.",
                "error",
            )
            return render_template("login.html")

        if not user or not password_hash or not check_password_hash(password_hash, password):
            if user:
                newly_blocked = increment_failed_attempts(user.id)
                # Reload user to get updated failed_attempts count
                user, _ = get_user_by_username(username)
                if newly_blocked:
                    flash(
                        "Your account has been blocked after too many failed attempts. "
                        "Please contact an administrator.",
                        "error",
                    )
                else:
                    remaining = max(0, 5 - user.failed_attempts)
                    flash(
                        f"Incorrect password. {remaining} attempt{'s' if remaining != 1 else ''} remaining before your account is blocked.",
                        "error",
                    )
            else:
                flash("Invalid username or password.", "error")
            return render_template("login.html")

        login_user(user)
        update_last_login(user.id)

        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
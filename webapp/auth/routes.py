from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from webapp.auth.db import get_user_by_username, update_last_login

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user, pw_hash = get_user_by_username(username)

        if user is None or not check_password_hash(pw_hash, password):
            flash("Invalid username or password.", "error")
            return render_template("login.html"), 401

        login_user(user, remember=False)
        update_last_login(user.id)
        next_page = request.args.get("next") or url_for("dashboard.index")
        return redirect(next_page)

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
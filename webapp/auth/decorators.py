from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            flash("This page requires administrator access.", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated
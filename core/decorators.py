from functools import wraps
from flask import session, redirect, url_for, flash  # type: ignore
from core.models import User  # type: ignore


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        user = User.query.get(session["user_id"])
        if not user or user.role != "admin":
            flash("관리자 권한이 필요합니다.")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)

    return decorated_function

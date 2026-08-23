import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import user_model
from utils.audit import clear_failures, is_locked, record_failure, write_audit
from utils.auth import safe_next

auth_bp = Blueprint("auth", __name__)


def _login_vars():
    return {
        "show_default_login": os.environ.get("VERA_SHOW_DEFAULT_LOGIN", "1") == "1"
    }


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if is_locked():
            flash("Too many failed sign-in attempts. Try again in 15 minutes.", "danger")
            return render_template("auth/login.html", **_login_vars())
        user = user_model.authenticate(
            request.form.get("username", "").strip(),
            request.form.get("password", ""),
        )
        if not user:
            record_failure()
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", **_login_vars())
        clear_failures()
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user.get("role") or "staff"
        session.permanent = True
        write_audit("LOGIN", "auth", "user", user["id"])
        nxt = safe_next(request.args.get("next") or request.form.get("next"), url_for("dashboard.dashboard"))
        return redirect(nxt)
    return render_template("auth/login.html", **_login_vars())


@auth_bp.route("/logout")
def logout():
    write_audit("LOGOUT", "auth", "user", session.get("user_id"))
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))

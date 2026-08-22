from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import user_model
from utils.auth import validate_csrf

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        validate_csrf()
        user = user_model.authenticate(
            request.form.get("username", "").strip(),
            request.form.get("password", ""),
        )
        if not user:
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html")
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        nxt = request.args.get("next") or url_for("dashboard.dashboard")
        return redirect(nxt)
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))

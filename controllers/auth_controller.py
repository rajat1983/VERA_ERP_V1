from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import user_model
from utils.audit import clear_failures, is_locked, record_failure, write_audit
from utils.auth import safe_next
from utils.mailer import send_email, ADMIN_EMAIL
from utils.uploads import save_user_photo

auth_bp = Blueprint("auth", __name__)


def _login_vars():
    return {}


def _send_html(to_email, subject, template, **context):
    html = render_template(template, **context)
    return send_email(to_email, subject, html)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") and request.method == "GET":
        return redirect(url_for("dashboard.dashboard"))
    if request.method == "POST":
        if is_locked():
            flash("Too many failed sign-in attempts. Try again in 15 minutes.", "danger")
            return render_template("auth/login.html", **_login_vars())
        user = user_model.authenticate(
            request.form.get("username", "").strip(),
            request.form.get("password", ""),
        )
        blocked = user_model.login_blocked_reason(user)
        if blocked:
            record_failure()
            flash(blocked, "danger")
            return render_template("auth/login.html", **_login_vars())
        clear_failures()
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["full_name"] = user.get("full_name") or user["username"]
        session["photo"] = user.get("photo")
        session["role"] = user.get("role") or "staff"
        session.permanent = True
        write_audit("LOGIN", "auth", "user", user["id"])
        nxt = safe_next(request.args.get("next") or request.form.get("next"), url_for("dashboard.dashboard"))
        return redirect(nxt)
    return render_template("auth/login.html", **_login_vars())


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard.dashboard"))
    form = {
        "full_name": request.form.get("full_name", ""),
        "email": request.form.get("email", ""),
        "mobile": request.form.get("mobile", ""),
        "username": request.form.get("username", ""),
    }
    if request.method == "POST":
        try:
            confirm = request.form.get("confirm_password") or ""
            password = request.form.get("password") or ""
            if password != confirm:
                raise ValueError("Password and confirmation do not match.")
            created = user_model.register_user(
                form["full_name"],
                form["email"],
                form["mobile"],
                form["username"],
                password,
            )
            photo = save_user_photo(request.files.get("photo"), created["id"])
            if photo:
                user_model.set_user_photo(created["id"], photo)
            _send_html(
                created["email"],
                "VERA ERP registration received",
                "emails/registration_pending.html",
                name=created["full_name"],
            )
            _send_html(
                ADMIN_EMAIL,
                "VERA ERP: new user pending approval",
                "emails/registration_admin.html",
                name=created["full_name"],
                username=created["username"],
                email=created["email"],
            )
            write_audit("REGISTER", "auth", "user", created["id"], created["username"])
            flash("Registration submitted. An admin must approve your account before you can sign in.", "success")
            return redirect(url_for("auth.login"))
        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Could not complete registration.", "danger")
    return render_template("auth/register.html", form=form)


@auth_bp.route("/activate/<token>")
def activate(token):
    try:
        user_model.activate_by_token(token)
        flash("Your account is active. You can sign in now.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Could not activate this account.", "danger")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    write_audit("LOGOUT", "auth", "user", session.get("user_id"))
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("auth.login"))

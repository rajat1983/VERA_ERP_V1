from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from models import user_model
from utils.audit import write_audit
from utils.auth import admin_required
from utils.mailer import send_email
from utils.uploads import save_user_photo

user_bp = Blueprint("users", __name__)


def _maybe_save_photo(user_id):
    photo = save_user_photo(request.files.get("photo"), user_id)
    if photo:
        user_model.set_user_photo(user_id, photo)
        if int(session.get("user_id") or 0) == int(user_id):
            session["photo"] = photo
    return photo


@user_bp.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get("user_id")
    user = user_model.get_user(user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        try:
            if request.form.get("intent") == "password":
                new_password = request.form.get("new_password") or ""
                confirm = request.form.get("confirm_password") or ""
                if new_password != confirm:
                    raise ValueError("New password and confirmation do not match.")
                user_model.change_own_password(
                    user_id,
                    request.form.get("current_password"),
                    new_password,
                )
                write_audit("UPDATE", "profile", "user", user_id, "password")
                flash("Password updated.", "success")
            else:
                saved = user_model.update_own_profile(
                    user_id,
                    request.form.get("full_name"),
                    request.form.get("email"),
                    request.form.get("mobile"),
                )
                session["full_name"] = saved["full_name"]
                _maybe_save_photo(user_id)
                write_audit("UPDATE", "profile", "user", user_id, "details")
                flash("Profile updated.", "success")
            return redirect(url_for("users.profile"))
        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Could not save the profile.", "danger")
        user = user_model.get_user(user_id)
    return render_template("users/profile.html", user=user)


@user_bp.route("/users")
@admin_required
def list_users():
    from models import subscription_model

    tenant_id = session.get("tenant_id")
    access = getattr(g, "subscription", None) or subscription_model.access(tenant_id)
    seats_used = user_model.count_seat_users(tenant_id)
    max_users = int(access.get("max_users") or 5)
    return render_template(
        "users/list.html",
        users=user_model.list_users(),
        roles=user_model.list_roles(),
        seats_used=seats_used,
        max_users=max_users,
        seats_full=seats_used >= max_users,
        access=access,
    )


@user_bp.route("/users/<int:id>")
@admin_required
def view_user(id):
    user = user_model.get_user(id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("users.list_users"))
    return render_template("users/view.html", user=user)


@user_bp.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    tenant_id = session.get("tenant_id")
    try:
        user_model.assert_seat_available(tenant_id)
    except ValueError as e:
        flash(str(e), "warning")
        return redirect(url_for("users.list_users"))
    if request.method == "POST":
        try:
            user_id = user_model.create_user(
                request.form.get("username"),
                request.form.get("password"),
                int(request.form.get("role_id")),
                request.form.get("is_active") == "1",
                request.form.get("full_name"),
                request.form.get("email"),
                request.form.get("mobile"),
            )
            _maybe_save_photo(user_id)
            write_audit("CREATE", "users", "user", user_id, request.form.get("username"))
            flash("User created.", "success")
            return redirect(url_for("users.view_user", id=user_id))
        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Could not create the user.", "danger")
    return render_template("users/form.html", user=None, roles=user_model.list_roles())


@user_bp.route("/users/<int:id>/edit", methods=["GET", "POST"])
@admin_required
def edit_user(id):
    user = user_model.get_user(id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("users.list_users"))
    if request.method == "POST":
        try:
            if int(session.get("user_id") or 0) == id and request.form.get("is_active") != "1":
                raise ValueError("You cannot deactivate your own account.")
            user_model.update_user(
                id,
                int(request.form.get("role_id")),
                request.form.get("is_active") == "1",
                request.form.get("password") or None,
                request.form.get("full_name"),
                request.form.get("email"),
                request.form.get("mobile"),
            )
            if int(session.get("user_id") or 0) == id:
                session["full_name"] = (request.form.get("full_name") or "").strip()
            _maybe_save_photo(id)
            write_audit("UPDATE", "users", "user", id)
            flash("User updated.", "success")
            return redirect(url_for("users.view_user", id=id))
        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Could not update the user.", "danger")
        user = user_model.get_user(id)
    return render_template("users/form.html", user=user, roles=user_model.list_roles())


def _send_approved_email(user):
    if not user.get("email"):
        return False
    html = render_template(
        "emails/account_approved.html",
        name=user.get("full_name") or user.get("username"),
        login_url=url_for("auth.login", _external=True),
    )
    return send_email(user["email"], "Your VERA ERP account is active", html)


@user_bp.route("/users/<int:id>/approve", methods=["POST"])
@admin_required
def approve_user(id):
    try:
        user = user_model.approve_registration(id)
        sent = _send_approved_email(user)
        write_audit("APPROVE", "users", "user", id)
        if sent:
            flash("User approved and activated. A sign-in email was sent.", "success")
        else:
            flash("User approved and activated. The email could not be sent — they can still sign in now.", "warning")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Could not approve this user.", "danger")
    nxt = request.form.get("next") or url_for("users.view_user", id=id)
    return redirect(nxt)


@user_bp.route("/users/<int:id>/reject", methods=["POST"])
@admin_required
def reject_user(id):
    try:
        user_model.reject_registration(id)
        write_audit("REJECT", "users", "user", id)
        flash("Registration rejected.", "warning")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Could not reject this user.", "danger")
    nxt = request.form.get("next") or url_for("users.list_users")
    return redirect(nxt)

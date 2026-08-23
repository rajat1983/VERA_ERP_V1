from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models import user_model
from utils.audit import write_audit
from utils.auth import admin_required

user_bp = Blueprint("users", __name__)


@user_bp.route("/users")
@admin_required
def list_users():
    return render_template("users/list.html", users=user_model.list_users(), roles=user_model.list_roles())


@user_bp.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    if request.method == "POST":
        try:
            user_model.create_user(
                request.form.get("username"),
                request.form.get("password"),
                int(request.form.get("role_id")),
                request.form.get("is_active") == "1",
            )
            write_audit("CREATE", "users", "user", None, request.form.get("username"))
            flash("User created.", "success")
            return redirect(url_for("users.list_users"))
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
            )
            write_audit("UPDATE", "users", "user", id)
            flash("User updated.", "success")
            return redirect(url_for("users.list_users"))
        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Could not update the user.", "danger")
        user = user_model.get_user(id)
    return render_template("users/form.html", user=user, roles=user_model.list_roles())

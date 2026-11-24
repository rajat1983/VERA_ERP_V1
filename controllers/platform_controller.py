from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from models import platform_user_model, tenant_model, user_model
from utils.audit import write_audit
from utils.tenant import bind_platform_session

platform_bp = Blueprint("platform", __name__, url_prefix="/platform")


@platform_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("platform_user_id") and request.method == "GET":
        return redirect(url_for("platform.home"))
    if request.method == "POST":
        user = platform_user_model.authenticate(
            request.form.get("email", ""),
            request.form.get("password", ""),
        )
        if not user:
            flash("Invalid email or password.", "danger")
            return render_template("platform/login.html")
        bind_platform_session(user)
        write_audit("LOGIN", "platform", "user", user["id"], user["email"])
        return redirect(url_for("platform.home"))
    return render_template("platform/login.html")


@platform_bp.route("/logout")
def logout():
    write_audit("LOGOUT", "platform", "user", session.get("platform_user_id"))
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("platform.login"))


@platform_bp.route("/")
def home():
    return render_template("platform/home.html", counts=tenant_model.counts())


@platform_bp.route("/shops")
def shops():
    q = request.args.get("q", "")
    status = request.args.get("status", "")
    if status not in ("", "active", "suspended"):
        status = ""
    rows = tenant_model.list_tenants(status=status or None, search=q)
    return render_template("platform/shops.html", shops=rows, q=q, status=status)


@platform_bp.route("/shops/add", methods=["GET", "POST"])
def shop_add():
    form = {
        "name": request.form.get("name", ""),
        "shop_code": request.form.get("shop_code", ""),
        "owner_name": request.form.get("owner_name", ""),
        "owner_email": request.form.get("owner_email", ""),
        "owner_username": request.form.get("owner_username", ""),
    }
    if request.method != "POST":
        return render_template("platform/shop_form.html", form=form)
    tenant = None
    try:
        tenant = tenant_model.create_tenant(form["name"], shop_code=form["shop_code"] or None)
        roles = {r["name"]: r["id"] for r in user_model.list_roles()}
        if "admin" not in roles:
            raise ValueError("Admin role is missing.")
        user_model.create_user(
            form["owner_username"],
            request.form.get("owner_password", ""),
            roles["admin"],
            is_active=1,
            full_name=form["owner_name"],
            email=form["owner_email"],
            tenant_id=tenant["id"],
        )
    except ValueError as exc:
        if tenant:
            tenant_model.delete_tenant(tenant["id"])
        flash(str(exc), "danger")
        return render_template("platform/shop_form.html", form=form)
    except Exception:
        if tenant:
            tenant_model.delete_tenant(tenant["id"])
        flash("Could not create shop. Use a unique shop code.", "danger")
        return render_template("platform/shop_form.html", form=form)
    write_audit("CREATE", "platform", "tenant", tenant["id"], tenant["shop_code"])
    flash(f"Shop {tenant['shop_code']} created.", "success")
    return redirect(url_for("platform.shop_view", id=tenant["id"]))


@platform_bp.route("/shops/<int:id>")
def shop_view(id):
    shop = tenant_model.get_by_id(id)
    if not shop:
        abort(404)
    users = tenant_model.list_shop_users(id)
    return render_template("platform/shop_view.html", shop=shop, users=users)


@platform_bp.route("/shops/<int:id>/status", methods=["POST"])
def shop_status(id):
    shop = tenant_model.get_by_id(id)
    if not shop:
        abort(404)
    try:
        tenant_model.set_status(id, request.form.get("status"))
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("platform.shop_view", id=id))
    write_audit("UPDATE", "platform", "tenant", id, request.form.get("status"))
    flash("Shop status updated.", "success")
    return redirect(url_for("platform.shop_view", id=id))

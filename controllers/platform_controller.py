from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from models import platform_settings_model, platform_user_model, subscription_model, tenant_model, user_model
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
        plans = subscription_model.list_plans()
        default_plan = next((p for p in plans if p["code"] == "Q12"), plans[0] if plans else None)
        if default_plan:
            subscription_model.activate(tenant["id"], default_plan["id"], note="Created by Super Admin")
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
    access = subscription_model.access(id)
    plans = subscription_model.list_plans()
    events = subscription_model.list_events(id)
    return render_template(
        "platform/shop_view.html",
        shop=shop,
        users=users,
        access=access,
        plans=plans,
        events=events,
        seats_used=user_model.count_seat_users(id),
        format_price=subscription_model.format_price,
    )


@platform_bp.route("/shops/<int:id>/subscription", methods=["POST"])
def shop_subscription(id):
    shop = tenant_model.get_by_id(id)
    if not shop:
        abort(404)
    action = (request.form.get("action") or "").strip().lower()
    try:
        if action == "activate":
            subscription_model.activate(id, request.form.get("plan_id"), note="Marked paid by Super Admin")
            flash("Subscription activated.", "success")
        elif action == "extend":
            subscription_model.extend(id, note="Extended by Super Admin")
            flash("Subscription extended.", "success")
        elif action == "suspend":
            subscription_model.set_subscription_status(id, "suspended", "Suspended by Super Admin")
            flash("Subscription suspended.", "success")
        else:
            flash("Unknown subscription action.", "danger")
    except ValueError as exc:
        flash(str(exc), "danger")
    write_audit("UPDATE", "platform", "subscription", id, action)
    return redirect(url_for("platform.shop_view", id=id))


@platform_bp.route("/shops/<int:id>/seats", methods=["POST"])
def shop_seats(id):
    shop = tenant_model.get_by_id(id)
    if not shop:
        abort(404)
    try:
        rupees = request.form.get("extra_user_price_rupees")
        price_paise = None if rupees in (None, "") else int(round(float(rupees) * 100))
        subscription_model.set_extra_seats(
            id,
            request.form.get("extra_users") or 0,
            price_paise,
        )
        flash("Shop user seats updated.", "success")
    except (TypeError, ValueError) as exc:
        flash(str(exc) if str(exc) else "Enter a valid extra user count and price.", "danger")
    write_audit("UPDATE", "platform", "seats", id, request.form.get("extra_users"))
    return redirect(url_for("platform.shop_view", id=id))


@platform_bp.route("/plans")
def plans():
    return render_template(
        "platform/plans.html",
        plans=subscription_model.list_plans(include_inactive=True),
        format_price=subscription_model.format_price,
    )


@platform_bp.route("/plans/<int:id>", methods=["GET", "POST"])
def plan_edit(id):
    plan = subscription_model.get_plan(id)
    if not plan:
        abort(404)
    if request.method == "POST":
        try:
            rupees = float(request.form.get("price_rupees") or 0)
            subscription_model.update_plan(
                id,
                request.form.get("name"),
                request.form.get("duration_days"),
                int(round(rupees * 100)),
                request.form.get("gst_rate") or 18,
                request.form.get("max_users") or 5,
                bool(request.form.get("is_public")),
                bool(request.form.get("is_active")),
                bool(request.form.get("allow_pos")),
                bool(request.form.get("allow_production")),
                bool(request.form.get("allow_services")),
                int(round(float(request.form.get("extra_user_price_rupees") or 0) * 100)),
            )
            flash("Plan saved.", "success")
            return redirect(url_for("platform.plans"))
        except ValueError as exc:
            flash(str(exc), "danger")
            plan = subscription_model.get_plan(id)
    return render_template("platform/plan_form.html", plan=plan)


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


@platform_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        platform_settings_model.save(
            {
                "default_grace_days": request.form.get("default_grace_days") or "7",
                "razorpay_key_id": request.form.get("razorpay_key_id") or "",
                "razorpay_key_secret": request.form.get("razorpay_key_secret") or "",
                "razorpay_webhook_secret": request.form.get("razorpay_webhook_secret") or "",
                "platform_gstin": request.form.get("platform_gstin") or "",
                "support_email": request.form.get("support_email") or "",
            }
        )
        flash("Platform settings saved.", "success")
        return redirect(url_for("platform.settings"))
    return render_template("platform/settings.html", settings=platform_settings_model.get_all())

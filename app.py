from datetime import timedelta
import logging
import os
import sys
import time

sys.path.append("/var/www/html")

from flask import Flask, flash, g, redirect, render_template, request, session, url_for

from controllers.employee_controller import employee_bp
from controllers.dashboard_controller import dashboard_bp
from controllers.product_controller import product_bp
from controllers.vendor_controller import vendor_bp
from controllers.customer_controller import customer_bp
from controllers.sales_controller import sales_bp
from controllers.purchase_controller import purchase_bp
from controllers.production_controller import production_bp
from controllers.admin_controller import admin_bp
from controllers.auth_controller import auth_bp
from controllers.inventory_controller import inventory_bp
from controllers.payment_controller import payment_bp
from controllers.report_controller import report_bp
from controllers.settings_controller import settings_bp
from controllers.user_controller import user_bp
from controllers.pos_controller import pos_bp
from controllers.service_controller import service_bp
from genai.routes.ai_routes import ai_bp
from controllers.platform_controller import platform_bp
from controllers.billing_controller import billing_bp
from controllers.legal_controller import legal_bp
from db import get_db_connection
from models import platform_user_model, subscription_model, user_model
from utils.auth import auth_enabled, csrf_token, validate_csrf, safe_next
from utils.entitlements import feature_for_path, from_access
from utils.permissions import can, enforce_request
from utils.schema import ensure_schema, ensure_roles_users
from utils.security import assert_production_safe, is_production

assert_production_safe()


def _secret_key():
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    if is_production():
        raise SystemExit("SECRET_KEY must be set when VERA_ENV=production.")
    print("WARNING: SECRET_KEY is not set. Set it in the environment before production.")
    return "insecure-dev-key"


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = _secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("VERA_COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.environ.get("VERA_SESSION_HOURS", "8"))),
)
def plan_allows(feature):
    ents = getattr(g, "entitlements", None)
    if ents is None:
        return True
    return bool(ents.get(feature, True))


app.jinja_env.globals["get_csrf_token"] = csrf_token
app.jinja_env.globals["can"] = can
app.jinja_env.globals["plan_allows"] = plan_allows

logging.basicConfig(
    level=os.environ.get("VERA_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
if os.environ.get("VERA_LOG_FILE"):
    logging.getLogger().addHandler(logging.FileHandler(os.environ["VERA_LOG_FILE"]))

try:
    ensure_schema()
except Exception as exc:
    print("Schema bootstrap skipped:", exc)
try:
    ensure_roles_users()
    user_model.ensure_default_admin()
    platform_user_model.bootstrap_from_env()
except Exception as exc:
    print("Users/roles bootstrap failed:", exc)

app.register_blueprint(auth_bp)
app.register_blueprint(employee_bp)
app.register_blueprint(product_bp)
app.register_blueprint(vendor_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(purchase_bp)
app.register_blueprint(production_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(report_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(user_bp)
app.register_blueprint(pos_bp)
app.register_blueprint(service_bp)
app.register_blueprint(platform_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(legal_bp)


def _safe_next(path):
    return safe_next(path, url_for("dashboard.dashboard"))


app.jinja_env.globals["safe_next"] = _safe_next


@app.route("/healthz")
def healthz():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 AS ok")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "db": "up"}, 200
    except Exception:
        return {"status": "degraded", "db": "down"}, 503


@app.errorhandler(403)
def forbidden(_e):
    if request.path.startswith("/api/"):
        return {"error": "permission denied"}, 403
    return render_template("errors/403_bounce.html"), 403


def _guard_upload_path():
    from flask import abort
    import re

    path = request.path or ""
    if not path.startswith("/static/uploads/"):
        return
    if session.get("platform_user_id") and not session.get("user_id"):
        return
    if not session.get("user_id") or not session.get("tenant_id"):
        abort(404)
    tenant_id = int(session["tenant_id"])
    name = path.rsplit("/", 1)[-1]
    if f"/t{tenant_id}/" in path or name.startswith("t%s_" % tenant_id):
        return
    match = re.match(r"user_(\d+)_", name)
    if match:
        owner = user_model.get_user(int(match.group(1)))
        if owner and int(owner.get("tenant_id") or 0) == tenant_id:
            return
    abort(404)


@app.before_request
def _guard():
    if request.endpoint == "static" or request.path.startswith("/static"):
        return _guard_upload_path()
    if request.endpoint in (None, "healthz"):
        return
    if request.path.startswith("/legal"):
        return
    if request.path == "/billing/razorpay/webhook":
        return
    idle = int(os.environ.get("VERA_IDLE_SECONDS", "28800"))
    if session.get("user_id") or session.get("platform_user_id"):
        last = session.get("_last_seen")
        now = time.time()
        if last and now - float(last) > idle:
            session.clear()
            if request.path.startswith("/platform"):
                return redirect(url_for("platform.login"))
            return redirect(url_for("auth.login"))
        session["_last_seen"] = now
        session.permanent = True
    public = {
        "auth.login",
        "auth.register",
        "auth.signup",
        "auth.activate",
        "auth.logout",
        "platform.login",
        "platform.logout",
        "legal.terms",
        "legal.privacy",
        "legal.refund",
    }
    if request.endpoint in public:
        if request.method == "POST":
            validate_csrf()
        return
    if request.path.startswith("/platform"):
        if auth_enabled() and not session.get("platform_user_id"):
            return redirect(url_for("platform.login", next=request.path))
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and auth_enabled():
            validate_csrf()
        return
    if session.get("platform_user_id") and not session.get("user_id"):
        from flask import abort
        abort(403)
    if auth_enabled() and not session.get("user_id"):
        return redirect(url_for("auth.login", next=request.path))
    if not session.get("tenant_id"):
        session.clear()
        if auth_enabled():
            return redirect(url_for("auth.login", next=request.path))
        from flask import abort
        abort(403)
    from models import tenant_model

    tenant = tenant_model.get_by_id(int(session["tenant_id"]))
    if not tenant:
        session.clear()
        return redirect(url_for("auth.login"))
    g.tenant_id = int(tenant["id"])
    session["tenant_id"] = g.tenant_id
    billing_ok = {
        "billing.expired",
        "billing.home",
        "billing.create_order",
        "billing.verify",
        "auth.logout",
        "users.profile",
    }
    tenant_ok = (tenant.get("status") or "").lower() == "active"
    if session.get("user_id"):
        access = subscription_model.access(g.tenant_id)
        g.subscription = access
        g.entitlements = from_access(access)
        allowed = bool(access.get("allowed")) and tenant_ok
        if not allowed and request.endpoint not in billing_ok:
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                validate_csrf()
            return redirect(url_for("billing.expired"))
        locked = feature_for_path(request.path)
        if allowed and locked and not g.entitlements.get(locked, True):
            flash(
                "Your plan does not include this module. Open Billing or ask Super Admin to enable it.",
                "warning",
            )
            return redirect(url_for("dashboard.dashboard"))
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and auth_enabled():
        validate_csrf()
    enforce_request()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1" and not is_production()
    app.run(debug=debug, host="0.0.0.0", port=5000)

from datetime import timedelta
import logging
import os
import sys
import time

sys.path.append("/var/www/html")

from flask import Flask, flash, redirect, render_template, request, session, url_for

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
from genai.routes.ai_routes import ai_bp
from models import user_model
from utils.auth import auth_enabled, csrf_token, validate_csrf, safe_next, safe_referer
from utils.permissions import can, enforce_request
from utils.schema import ensure_schema, ensure_roles_users


def _secret_key():
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
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
app.jinja_env.globals["get_csrf_token"] = csrf_token
app.jinja_env.globals["can"] = can

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


def _safe_next(path):
    return safe_next(path, url_for("dashboard.dashboard"))


app.jinja_env.globals["safe_next"] = _safe_next


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


@app.errorhandler(403)
def forbidden(_e):
    if request.path.startswith("/api/"):
        return {"error": "permission denied"}, 403
    flash("You do not have permission for that action.", "permission")
    return redirect(safe_referer(url_for("dashboard.dashboard")))


@app.before_request
def _guard():
    if request.endpoint in (None, "static", "healthz") or request.path.startswith("/static"):
        return
    idle = int(os.environ.get("VERA_IDLE_SECONDS", "28800"))
    if session.get("user_id"):
        last = session.get("_last_seen")
        now = time.time()
        if last and now - float(last) > idle:
            session.clear()
            return redirect(url_for("auth.login"))
        session["_last_seen"] = now
        session.permanent = True
    if request.endpoint == "auth.login":
        if request.method == "POST":
            validate_csrf()
        return
    if auth_enabled() and not session.get("user_id"):
        return redirect(url_for("auth.login", next=request.path))
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and auth_enabled():
        validate_csrf()
    enforce_request()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=5000)

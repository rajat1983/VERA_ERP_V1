from flask import Flask
import os
import sys

sys.path.append("/var/www/html")

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
from genai.routes.ai_routes import ai_bp
from utils.schema import ensure_schema
from utils.auth import auth_enabled, csrf_token, validate_csrf
from models import user_model


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "secret123")
app.jinja_env.globals["get_csrf_token"] = csrf_token

try:
    ensure_schema()
    user_model.ensure_default_admin()
except Exception as exc:
    print("Schema bootstrap skipped:", exc)

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


@app.before_request
def _guard():
    from flask import request, session, redirect, url_for
    if request.endpoint in (None, "static", "auth.login"):
        return
    if request.path.startswith("/static"):
        return
    if auth_enabled() and not session.get("user_id"):
        return redirect(url_for("auth.login", next=request.path))
    if request.method == "POST" and auth_enabled():
        validate_csrf()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", host="0.0.0.0", port=5000)

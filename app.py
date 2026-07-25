from flask import Flask
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
from genai.routes.ai_routes import ai_bp


app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "secret123"

app.register_blueprint(employee_bp)
app.register_blueprint(product_bp)
app.register_blueprint(vendor_bp)
app.register_blueprint(customer_bp)
app.register_blueprint(sales_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(purchase_bp)
app.register_blueprint(production_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)






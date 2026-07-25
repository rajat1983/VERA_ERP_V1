from flask import Blueprint, render_template
from models import dashboard_model

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
def dashboard():

    sales_by_date = dashboard_model.get_sales_by_date()
    top_products = dashboard_model.get_top_products()
    top_customers = dashboard_model.get_top_customers()
    stock_levels = dashboard_model.get_stock_levels()

    return render_template(
        "/dashboard.html",
        sales_by_date=sales_by_date,
        top_products=top_products,
        top_customers=top_customers,
        stock_levels=stock_levels
    )

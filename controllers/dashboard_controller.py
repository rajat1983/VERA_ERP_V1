from flask import Blueprint, render_template
from models import dashboard_model

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
def dashboard():

    # Dashboard KPIs
    kpi = dashboard_model.get_dashboard_kpi()

    # Existing Data
    sales_by_date = dashboard_model.get_sales_by_date()
    top_products = dashboard_model.get_top_products()
    top_customers = dashboard_model.get_top_customers()
    stock_levels = dashboard_model.get_stock_levels()
    insights = dashboard_model.get_business_insights()
    recent_transactions = dashboard_model.get_recent_transactions()
    low_stock_products = dashboard_model.get_low_stock_products()
    alerts = dashboard_model.get_dashboard_alerts()

    return render_template(
        "dashboard.html",

        kpi=kpi,
        insights=insights,
        recent_transactions=recent_transactions,
        sales_by_date=sales_by_date,
        top_products=top_products,
        top_customers=top_customers,
        stock_levels=stock_levels,
        low_stock_products=low_stock_products,
        alerts=alerts
    )
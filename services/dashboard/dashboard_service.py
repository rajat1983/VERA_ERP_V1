from datetime import date, timedelta

from models import dashboard_model
from models import payment_model
from services.dashboard.business_health_service import BusinessHealthService


def _payables():
    try:
        return payment_model.payables_outstanding()
    except Exception:
        return 0.0


class DashboardService:

    @staticmethod
    def load_dashboard(from_date=None, to_date=None):
        from_date = (from_date or "").strip() or None
        to_date = (to_date or "").strip() or None
        if not from_date and not to_date:
            to_date = date.today().isoformat()
            from_date = (date.today() - timedelta(days=30)).isoformat()

        return {
            "kpi": dashboard_model.get_dashboard_kpi(),
            "payments": dashboard_model.get_payment_overview(),
            "outstanding_invoices": dashboard_model.get_outstanding_invoices(),
            "recent_payments": dashboard_model.get_recent_payments(),
            "health": BusinessHealthService.calculate(),
            "insights": dashboard_model.get_business_insights(),
            "alerts": dashboard_model.get_dashboard_alerts(),
            "low_stock_products": dashboard_model.get_low_stock_products(),
            "recent_transactions": dashboard_model.get_recent_transactions(),
            "payables_outstanding": _payables(),
            "sales_by_date": dashboard_model.get_sales_by_date(from_date, to_date),
            "top_products": dashboard_model.get_top_products(),
            "top_customers": dashboard_model.get_top_customers(),
            "stock_levels": dashboard_model.get_stock_levels(),
            "from_date": from_date or "",
            "to_date": to_date or "",
        }
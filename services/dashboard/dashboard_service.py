from models import dashboard_model
from services.dashboard.business_health_service import BusinessHealthService


class DashboardService:

    @staticmethod
    def load_dashboard(from_date=None, to_date=None):

        return {

            "kpi": dashboard_model.get_dashboard_kpi(),

            "health": BusinessHealthService.calculate(),

            "insights": dashboard_model.get_business_insights(),

            "alerts": dashboard_model.get_dashboard_alerts(),

            "low_stock_products": dashboard_model.get_low_stock_products(),

            "recent_transactions": dashboard_model.get_recent_transactions(),

            "sales_by_date": dashboard_model.get_sales_by_date(from_date, to_date),

            "top_products": dashboard_model.get_top_products(),

            "top_customers": dashboard_model.get_top_customers(),

            "stock_levels": dashboard_model.get_stock_levels(),

            "from_date": from_date or "",

            "to_date": to_date or ""

        }
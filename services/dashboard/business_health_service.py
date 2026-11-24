from db import get_db_connection
from config.business_health_rules import BUSINESS_HEALTH
from config.business_health_rules import ( BUSINESS_HEALTH, STATUS)
from utils.tenant import tid
class BusinessHealthService:

    @staticmethod
    def calculate():

        conn = get_db_connection()
        cur = conn.cursor()

        score = 100
        reasons = []

        # ==========================================
        # 1. Low Stock Health
        # ==========================================

        cur.execute("""
            SELECT COUNT(*) total
            FROM products
            WHERE tenant_id=%s AND stock_qty <= low_stock_threshold
        """, (tid(),))

        low_stock = cur.fetchone()["total"]

        if low_stock > 0:
            deduction = min(
            low_stock * 2,
            BUSINESS_HEALTH["LOW_STOCK_WEIGHT"]
        )
            score -= deduction

            reasons.append({
                "type": "warning",
                "title": "Low Stock",
                "message": f"{low_stock} products require replenishment."
            })

        # ==========================================
        # 2. Pending Customer Payments
        # ==========================================

        cur.execute("""
            SELECT COUNT(*) total
            FROM sales
            WHERE tenant_id=%s AND payment_status='Pending'
              AND IFNULL(sale_status, 'Confirmed') <> 'Cancelled'
        """, (tid(),))

        pending = cur.fetchone()["total"]

        if pending > 0:
            deduction = min(
            pending * 3,
            BUSINESS_HEALTH["PENDING_PAYMENT_WEIGHT"]
        )
            score -= deduction

            reasons.append({
                "type": "danger",
                "title": "Pending Payments",
                "message": f"{pending} customer payments are pending."
            })

        # ==========================================
        # 3. Sales Activity
        # ==========================================

        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM sales
                  WHERE tenant_id=%s AND DATE(sale_date)=CURDATE()
                    AND IFNULL(sale_status, 'Confirmed') <> 'Cancelled')
                +
                (SELECT COUNT(*) FROM pos_sales
                  WHERE tenant_id=%s AND DATE(sale_date)=CURDATE())
                AS total
        """, (tid(), tid()))

        today_sales = cur.fetchone()["total"]

        if today_sales == 0:

            score -= BUSINESS_HEALTH["SALES_ACTIVITY_WEIGHT"]

            reasons.append({
                "type": "info",
                "title": "Sales",
                "message": "No sales recorded today."
            })

        # ==========================================
        # Final Score
        # ==========================================

        score = max(score, 0)

        if score >= STATUS["EXCELLENT"]:
            status = "Excellent"
            color = "success"

        elif score >= STATUS["GOOD"]:
            status = "Good"
            color = "primary"

        elif score >= STATUS["AVERAGE"]:
            status = "Average"
            color = "warning"

        else:
            status = "Critical"
            color = "danger"

        conn.close()

        return {
            "score": score,
            "status": status,
            "color": color,
            "reasons": reasons
        }
from db import get_db_connection
from utils.tenant import tid
from decimal import Decimal


def normalize(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


# -----------------------------
# Dashboard KPI
# -----------------------------
def get_dashboard_kpi():

    conn = get_db_connection()
    cur = conn.cursor()

    tenant_id = tid()
    cur.execute(
        """
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM sales
        WHERE tenant_id=%s AND DATE(sale_date)=CURDATE()
          AND IFNULL(sale_status, 'Confirmed') <> 'Cancelled'
        """,
        (tenant_id,),
    )
    today_sales = float(cur.fetchone()["total"])
    cur.execute(
        """
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM pos_sales
        WHERE tenant_id=%s AND DATE(sale_date)=CURDATE()
        """,
        (tenant_id,),
    )
    today_sales += float(cur.fetchone()["total"])

    cur.execute(
        """
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM purchases
        WHERE tenant_id=%s AND DATE(purchase_date)=CURDATE()
        """,
        (tenant_id,),
    )
    today_purchase = float(cur.fetchone()["total"])

    cur.execute("SELECT COUNT(*) AS total FROM products WHERE tenant_id=%s", (tenant_id,))
    total_products = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM customers WHERE tenant_id=%s", (tenant_id,))
    total_customers = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM vendors WHERE tenant_id=%s", (tenant_id,))
    total_vendors = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM products
        WHERE tenant_id=%s AND stock_qty <= low_stock_threshold
        """,
        (tenant_id,),
    )
    low_stock = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT IFNULL(SUM(stock_qty * cost_price),0) AS total
        FROM products
        WHERE tenant_id=%s
        """,
        (tenant_id,),
    )
    inventory_value = float(cur.fetchone()["total"])
    cur.execute(
        """
        SELECT
            IFNULL(SUM((si.price - p.cost_price) * si.qty), 0) AS profit
        FROM sale_items si
        INNER JOIN sales s
            ON s.id = si.sale_id
        INNER JOIN products p
            ON p.id = si.product_id
        WHERE s.tenant_id=%s AND DATE(s.sale_date) = CURDATE()
          AND IFNULL(s.sale_status, 'Confirmed') <> 'Cancelled'
        """,
        (tenant_id,),
    )

    today_profit = float(cur.fetchone()["profit"])
    cur.execute(
        """
        SELECT
            IFNULL(SUM((psi.price - p.cost_price) * psi.qty), 0) AS profit
        FROM pos_sale_items psi
        INNER JOIN pos_sales ps
            ON ps.id = psi.pos_sale_id
        INNER JOIN products p
            ON p.id = psi.product_id
        WHERE ps.tenant_id=%s AND DATE(ps.sale_date) = CURDATE()
          AND psi.item_type = 'product'
        """,
        (tenant_id,),
    )
    today_profit += float(cur.fetchone()["profit"])
    #"today_profit": today_profit,

    conn.close()

    return {
        "today_sales": today_sales,
        "today_purchase": today_purchase,
        "today_profit": today_profit,
        "products": total_products,
        "customers": total_customers,
        "vendors": total_vendors,
        "low_stock": low_stock,
        "inventory_value": inventory_value
    }


# -----------------------------
# Sales Chart
# -----------------------------
def get_sales_by_date(from_date=None, to_date=None):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT date, SUM(total) AS total
        FROM (
            SELECT DATE(sale_date) AS date, SUM(total_amount) AS total
            FROM sales
            WHERE tenant_id=%s
              AND IFNULL(sale_status, 'Confirmed') <> 'Cancelled'
              AND (%s IS NULL OR DATE(sale_date) >= %s)
              AND (%s IS NULL OR DATE(sale_date) <= %s)
            GROUP BY DATE(sale_date)
            UNION ALL
            SELECT DATE(sale_date) AS date, SUM(total_amount) AS total
            FROM pos_sales
            WHERE tenant_id=%s
              AND (%s IS NULL OR DATE(sale_date) >= %s)
              AND (%s IS NULL OR DATE(sale_date) <= %s)
            GROUP BY DATE(sale_date)
        ) combined
        GROUP BY date
        ORDER BY date ASC
    """, (
        tid(), from_date, from_date, to_date, to_date,
        tid(), from_date, from_date, to_date, to_date,
    ))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "date": str(r["date"]),
            "total": float(r["total"])
        }
        for r in rows
    ]


# -----------------------------
# Top Selling Products
# -----------------------------
def get_top_products():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, SUM(total_qty) AS total_qty
        FROM (
            SELECT p.id,
                   CONVERT(p.name USING utf8mb4) COLLATE utf8mb4_unicode_ci AS name,
                   SUM(i.qty) AS total_qty
            FROM sale_items i
            JOIN products p ON p.id=i.product_id
            JOIN sales s ON s.id=i.sale_id
            WHERE p.tenant_id=%s AND IFNULL(s.sale_status, 'Confirmed') <> 'Cancelled'
            GROUP BY p.id, CONVERT(p.name USING utf8mb4) COLLATE utf8mb4_unicode_ci
            UNION ALL
            SELECT p.id,
                   CONVERT(p.name USING utf8mb4) COLLATE utf8mb4_unicode_ci AS name,
                   SUM(psi.qty) AS total_qty
            FROM pos_sale_items psi
            JOIN products p ON p.id=psi.product_id
            JOIN pos_sales ps ON ps.id=psi.pos_sale_id
            WHERE p.tenant_id=%s AND psi.item_type='product'
            GROUP BY p.id, CONVERT(p.name USING utf8mb4) COLLATE utf8mb4_unicode_ci
        ) x
        GROUP BY id, name
        ORDER BY total_qty DESC
        LIMIT 5
    """, (tid(), tid()))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "name": r["name"],
            "total_qty": int(r["total_qty"])
        }
        for r in rows
    ]


# -----------------------------
# Top Customers
# -----------------------------
def get_top_customers():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.name,
            SUM(s.total_amount) AS total_spent
        FROM sales s
        JOIN customers c
            ON c.id=s.customer_id AND c.tenant_id=s.tenant_id
        WHERE s.tenant_id=%s AND IFNULL(s.sale_status, 'Confirmed') <> 'Cancelled'
        GROUP BY c.id
        ORDER BY total_spent DESC
        LIMIT 5
    """, (tid(),))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "name": r["name"],
            "total_spent": float(r["total_spent"])
        }
        for r in rows
    ]


# -----------------------------
# Stock Levels
# -----------------------------
def get_stock_levels():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            name,
            stock_qty
        FROM products
        WHERE tenant_id=%s
        ORDER BY stock_qty ASC
        LIMIT 10
    """, (tid(),))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "name": r["name"],
            "stock_qty": int(r["stock_qty"])
        }
        for r in rows
    ]
def get_business_insights():

    conn = get_db_connection()
    cur = conn.cursor()

    # Top Product
    cur.execute("""
        SELECT p.name,
               SUM(si.qty) qty
        FROM sale_items si
        JOIN products p
          ON p.id=si.product_id
        WHERE p.tenant_id=%s
        GROUP BY p.id
        ORDER BY qty DESC
        LIMIT 1
    """, (tid(),))

    top_product = cur.fetchone()

    # Top Customer
    cur.execute("""
        SELECT c.name,
               SUM(s.total_amount) amount
        FROM sales s
        JOIN customers c
          ON c.id=s.customer_id AND c.tenant_id=s.tenant_id
        WHERE s.tenant_id=%s AND IFNULL(s.sale_status, 'Confirmed') <> 'Cancelled'
        GROUP BY c.id
        ORDER BY amount DESC
        LIMIT 1
    """, (tid(),))

    top_customer = cur.fetchone()

    # Top Vendor
    cur.execute("""
        SELECT v.name,
               COUNT(*) total_purchase
        FROM purchases p
        JOIN vendors v
          ON v.id=p.vendor_id AND v.tenant_id=p.tenant_id
        WHERE p.tenant_id=%s
        GROUP BY v.id
        ORDER BY total_purchase DESC
        LIMIT 1
    """, (tid(),))

    top_vendor = cur.fetchone()

    conn.close()

    return {
        "top_product": top_product,
        "top_customer": top_customer,
        "top_vendor": top_vendor
    }
def get_recent_transactions():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        (
            SELECT
                sale_date      AS trans_date,
                CONVERT(invoice_no USING utf8mb4) COLLATE utf8mb4_unicode_ci AS number,
                customer_id,
                total_amount   AS amount,
                CONVERT('Sale' USING utf8mb4) COLLATE utf8mb4_unicode_ci AS module
            FROM sales
            WHERE tenant_id=%s
              AND IFNULL(sale_status, 'Confirmed') <> 'Cancelled'
        )

        UNION ALL

        (
            SELECT
                sale_date,
                CONVERT(bill_no USING utf8mb4) COLLATE utf8mb4_unicode_ci,
                customer_id,
                total_amount,
                CONVERT('POS' USING utf8mb4) COLLATE utf8mb4_unicode_ci
            FROM pos_sales
            WHERE tenant_id=%s
        )

        UNION ALL

        (
            SELECT
                purchase_date,
                CONVERT(vendor_invoice_no USING utf8mb4) COLLATE utf8mb4_unicode_ci,
                vendor_id,
                total_amount,
                CONVERT('Purchase' USING utf8mb4) COLLATE utf8mb4_unicode_ci
            FROM purchases
            WHERE tenant_id=%s
        )

        ORDER BY trans_date DESC
        LIMIT 10
    """, (tid(), tid(), tid()))

    rows = cur.fetchall()
    conn.close()

    return rows

def get_low_stock_products():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            name,
            stock_qty,
            low_stock_threshold
        FROM products
        WHERE tenant_id=%s AND stock_qty <= low_stock_threshold
        ORDER BY stock_qty ASC
    """, (tid(),))

    rows = cur.fetchall()
    conn.close()

    return rows
def get_dashboard_alerts():

    conn = get_db_connection()
    cur = conn.cursor()

    alerts = []

    # Low Stock
    cur.execute("""
        SELECT COUNT(*) total
        FROM products
        WHERE tenant_id=%s AND stock_qty <= low_stock_threshold
    """, (tid(),))

    low_stock = cur.fetchone()["total"]

    if low_stock > 0:
        alerts.append({
            "type": "danger",
            "icon": "⚠",
            "message": f"{low_stock} Products below reorder level"
        })

    # Pending Customer Payments (open confirmed invoices only)
    cur.execute("""
        SELECT COUNT(*) total
        FROM sales
        WHERE tenant_id=%s AND sale_status='Confirmed'
          AND payment_status IN ('Pending', 'Partial')
    """, (tid(),))

    pending = cur.fetchone()["total"]

    if pending > 0:
        alerts.append({
            "type": "warning",
            "icon": "💰",
            "message": f"{pending} invoices with unpaid balance"
        })

    conn.close()

    return alerts


def get_payment_overview():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS total
        FROM payments
        WHERE tenant_id=%s AND payment_date = CURDATE()
    """, (tid(),))
    collected_today = float(cur.fetchone()["total"])
    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS total
        FROM pos_payments pp
        JOIN pos_sales ps ON ps.id = pp.pos_sale_id
        WHERE ps.tenant_id=%s AND DATE(ps.sale_date) = CURDATE()
    """, (tid(),))
    collected_today += float(cur.fetchone()["total"])

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS total
        FROM payments
        WHERE tenant_id=%s
          AND YEAR(payment_date) = YEAR(CURDATE())
          AND MONTH(payment_date) = MONTH(CURDATE())
    """, (tid(),))
    collected_month = float(cur.fetchone()["total"])
    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS total
        FROM pos_payments pp
        JOIN pos_sales ps ON ps.id = pp.pos_sale_id
        WHERE ps.tenant_id=%s
          AND YEAR(ps.sale_date) = YEAR(CURDATE())
          AND MONTH(ps.sale_date) = MONTH(CURDATE())
    """, (tid(),))
    collected_month += float(cur.fetchone()["total"])

    cur.execute("""
        SELECT
            COUNT(*) AS invoice_count,
            IFNULL(SUM(total_amount - IFNULL(paid_amount, 0)), 0) AS outstanding
        FROM sales
        WHERE tenant_id=%s AND sale_status = 'Confirmed'
          AND IFNULL(paid_amount, 0) < total_amount
    """, (tid(),))
    due = cur.fetchone()

    cur.execute("""
        SELECT
            IFNULL(SUM(payment_status = 'Pending'), 0) AS pending,
            IFNULL(SUM(payment_status = 'Partial'), 0) AS partial,
            IFNULL(SUM(payment_status = 'Paid'), 0) AS paid
        FROM sales
        WHERE tenant_id=%s AND sale_status = 'Confirmed'
    """, (tid(),))
    status = cur.fetchone()

    conn.close()
    return {
        "collected_today": collected_today,
        "collected_month": collected_month,
        "outstanding_amount": float(due["outstanding"]),
        "outstanding_count": int(due["invoice_count"] or 0),
        "pending_count": int(status["pending"] or 0),
        "partial_count": int(status["partial"] or 0),
        "paid_count": int(status["paid"] or 0),
    }


def get_outstanding_invoices(limit=8):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            s.id,
            s.invoice_no,
            s.sale_date,
            s.total_amount,
            IFNULL(s.paid_amount, 0) AS paid_amount,
            s.payment_status,
            c.name AS customer_name
        FROM sales s
        JOIN customers c ON c.id = s.customer_id AND c.tenant_id = s.tenant_id
        WHERE s.tenant_id=%s AND s.sale_status = 'Confirmed'
          AND IFNULL(s.paid_amount, 0) < s.total_amount
        ORDER BY s.sale_date ASC, s.id ASC
        LIMIT %s
        """,
        (tid(), limit),
    )
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        total = float(r["total_amount"] or 0)
        paid = float(r["paid_amount"] or 0)
        result.append({
            "id": r["id"],
            "invoice_no": r["invoice_no"],
            "sale_date": r["sale_date"],
            "customer_name": r["customer_name"],
            "total_amount": total,
            "paid_amount": paid,
            "due_amount": round(total - paid, 2),
            "payment_status": r["payment_status"],
        })
    return result


def get_recent_payments(limit=8):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            p.payment_date,
            p.amount,
            p.payment_mode,
            p.reference_no,
            s.invoice_no,
            s.id AS sale_id,
            c.name AS customer_name
        FROM payments p
        JOIN sales s ON s.id = p.sale_id
        JOIN customers c ON c.id = s.customer_id AND c.tenant_id = s.tenant_id
        WHERE s.tenant_id=%s
        ORDER BY p.id DESC
        LIMIT %s
        """,
        (tid(), limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "payment_date": r["payment_date"],
            "amount": float(r["amount"] or 0),
            "payment_mode": r["payment_mode"],
            "reference_no": r["reference_no"],
            "invoice_no": r["invoice_no"],
            "sale_id": r["sale_id"],
            "customer_name": r["customer_name"],
        }
        for r in rows
    ]

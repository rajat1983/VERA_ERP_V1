from db import get_db_connection
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

    # Today's Sales
    cur.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM sales
        WHERE DATE(sale_date)=CURDATE()
    """)
    today_sales = float(cur.fetchone()["total"])

    # Today's Purchase
    cur.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS total
        FROM purchases
        WHERE DATE(purchase_date)=CURDATE()
    """)
    today_purchase = float(cur.fetchone()["total"])

    # Total Products
    cur.execute("SELECT COUNT(*) AS total FROM products")
    total_products = cur.fetchone()["total"]

    # Total Customers
    cur.execute("SELECT COUNT(*) AS total FROM customers")
    total_customers = cur.fetchone()["total"]

    # Total Suppliers
    cur.execute("SELECT COUNT(*) AS total FROM vendors ")
    total_vendors = cur.fetchone()["total"]

    # Low Stock Products
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM products
        WHERE stock_qty <= low_stock_threshold
    """)
    low_stock = cur.fetchone()["total"]

    # Inventory Value
    cur.execute("""
        SELECT IFNULL(SUM(stock_qty * cost_price),0) AS total
        FROM products
    """)
    inventory_value = float(cur.fetchone()["total"])
        # Today's Gross Profit
    cur.execute("""
        SELECT
            IFNULL(SUM((si.price - p.cost_price) * si.qty), 0) AS profit
        FROM sale_items si
        INNER JOIN sales s
            ON s.id = si.sale_id
        INNER JOIN products p
            ON p.id = si.product_id
        WHERE DATE(s.sale_date) = CURDATE()
    """)

    today_profit = float(cur.fetchone()["profit"])
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
        SELECT DATE(sale_date) AS date,
               SUM(total_amount) AS total
        FROM sales
        WHERE (%s IS NULL OR DATE(sale_date) >= %s)
          AND (%s IS NULL OR DATE(sale_date) <= %s)
        GROUP BY DATE(sale_date)
        ORDER BY date ASC
    """, (from_date, from_date, to_date, to_date))

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
        SELECT
            p.name,
            SUM(i.qty) AS total_qty
        FROM sale_items i
        JOIN products p
            ON p.id=i.product_id
        GROUP BY p.id
        ORDER BY total_qty DESC
        LIMIT 5
    """)

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
            ON c.id=s.customer_id
        GROUP BY c.id
        ORDER BY total_spent DESC
        LIMIT 5
    """)

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
        ORDER BY stock_qty ASC
        LIMIT 10
    """)

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
        GROUP BY p.id
        ORDER BY qty DESC
        LIMIT 1
    """)

    top_product = cur.fetchone()

    # Top Customer
    cur.execute("""
        SELECT c.name,
               SUM(s.total_amount) amount
        FROM sales s
        JOIN customers c
          ON c.id=s.customer_id
        GROUP BY c.id
        ORDER BY amount DESC
        LIMIT 1
    """)

    top_customer = cur.fetchone()

    # Top Vendor
    cur.execute("""
        SELECT v.name,
               COUNT(*) total_purchase
        FROM purchases p
        JOIN vendors v
          ON v.id=p.vendor_id
        GROUP BY v.id
        ORDER BY total_purchase DESC
        LIMIT 1
    """)

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
                invoice_no     AS number,
                customer_id,
                total_amount   AS amount,
                'Sale'         AS module
            FROM sales
        )

        UNION ALL

        (
            SELECT
                purchase_date,
                vendor_invoice_no,
                vendor_id,
                total_amount,
                'Purchase'
            FROM purchases
        )

        ORDER BY trans_date DESC
        LIMIT 10
    """)

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
        WHERE stock_qty <= low_stock_threshold
        ORDER BY stock_qty ASC
    """)

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
        WHERE stock_qty <= low_stock_threshold
    """)

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
        WHERE sale_status='Confirmed'
          AND payment_status IN ('Pending', 'Partial')
    """)

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
        WHERE payment_date = CURDATE()
    """)
    collected_today = float(cur.fetchone()["total"])

    cur.execute("""
        SELECT IFNULL(SUM(amount), 0) AS total
        FROM payments
        WHERE YEAR(payment_date) = YEAR(CURDATE())
          AND MONTH(payment_date) = MONTH(CURDATE())
    """)
    collected_month = float(cur.fetchone()["total"])

    cur.execute("""
        SELECT
            COUNT(*) AS invoice_count,
            IFNULL(SUM(total_amount - IFNULL(paid_amount, 0)), 0) AS outstanding
        FROM sales
        WHERE sale_status = 'Confirmed'
          AND IFNULL(paid_amount, 0) < total_amount
    """)
    due = cur.fetchone()

    cur.execute("""
        SELECT
            IFNULL(SUM(payment_status = 'Pending'), 0) AS pending,
            IFNULL(SUM(payment_status = 'Partial'), 0) AS partial,
            IFNULL(SUM(payment_status = 'Paid'), 0) AS paid
        FROM sales
        WHERE sale_status = 'Confirmed'
    """)
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
        JOIN customers c ON c.id = s.customer_id
        WHERE s.sale_status = 'Confirmed'
          AND IFNULL(s.paid_amount, 0) < s.total_amount
        ORDER BY s.sale_date ASC, s.id ASC
        LIMIT %s
        """,
        (limit,),
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
        JOIN customers c ON c.id = s.customer_id
        ORDER BY p.id DESC
        LIMIT %s
        """,
        (limit,),
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

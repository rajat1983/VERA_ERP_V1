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
def get_sales_by_date():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DATE(sale_date) AS date,
               SUM(total_amount) AS total
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY date ASC
    """)

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

        SELECT
            invoice_no number,
            sale_date trans_date,
            total_amount,
            'Sale' module
        FROM sales

        ORDER BY sale_date DESC

        LIMIT 5

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
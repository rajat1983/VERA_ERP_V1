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

    conn.close()

    return {
        "today_sales": today_sales,
        "today_purchase": today_purchase,
        "today_profit": today_sales - today_purchase,
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
from db import get_db_connection
from decimal import Decimal

def normalize(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def get_sales_by_date():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE(sale_date) as date, SUM(total_amount) as total
        FROM sales
        GROUP BY DATE(sale_date)
        ORDER BY date ASC
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {"date": str(r["date"]), "total": float(r["total"])}
        for r in rows
    ]


def get_top_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.name, SUM(i.qty) as total_qty
        FROM sale_items i
        JOIN products p ON p.id = i.product_id
        GROUP BY p.id
        ORDER BY total_qty DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {"name": r["name"], "total_qty": int(r["total_qty"])}
        for r in rows
    ]


def get_top_customers():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name, SUM(s.total_amount) as total_spent
        FROM sales s
        JOIN customers c ON c.id = s.customer_id
        GROUP BY c.id
        ORDER BY total_spent DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {"name": r["name"], "total_spent": float(r["total_spent"])}
        for r in rows
    ]


def get_stock_levels():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name, stock_qty
        FROM products
        ORDER BY stock_qty ASC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    return [
        {"name": r["name"], "stock_qty": int(r["stock_qty"])}
        for r in rows
    ]

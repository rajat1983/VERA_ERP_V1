from db import get_db_connection


def _dates(from_date, to_date):
    return from_date or "1970-01-01", to_date or "2099-12-31"


def sales_report(from_date, to_date):
    conn = get_db_connection()
    cur = conn.cursor()
    start, end = _dates(from_date, to_date)
    cur.execute(
        """
        SELECT s.invoice_no, s.sale_date, c.name AS customer_name,
               s.discount, s.gst_amount, s.total_amount, s.sale_status, s.payment_status
        FROM sales s
        JOIN customers c ON c.id = s.customer_id
        WHERE DATE(s.sale_date) BETWEEN %s AND %s
        ORDER BY s.id DESC
        """,
        (start, end),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def purchase_report(from_date, to_date):
    conn = get_db_connection()
    cur = conn.cursor()
    start, end = _dates(from_date, to_date)
    cur.execute(
        """
        SELECT p.purchase_no, p.purchase_date, v.name AS vendor_name,
               p.discount, p.gst_amount, p.total_amount, p.status
        FROM purchases p
        JOIN vendors v ON v.id = p.vendor_id
        WHERE DATE(p.purchase_date) BETWEEN %s AND %s
        ORDER BY p.id DESC
        """,
        (start, end),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def stock_report():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sku, name, stock_qty, reorder_level, cost_price, selling_price, status
        FROM products
        ORDER BY name
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def low_stock_report():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sku, name, stock_qty, reorder_level, IFNULL(low_stock_threshold, reorder_level) AS threshold
        FROM products
        WHERE stock_qty <= IFNULL(low_stock_threshold, reorder_level)
        ORDER BY stock_qty
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def payment_report(from_date, to_date):
    conn = get_db_connection()
    cur = conn.cursor()
    start, end = _dates(from_date, to_date)
    cur.execute(
        """
        SELECT p.payment_date, p.amount, p.payment_mode, p.reference_no,
               s.invoice_no, c.name AS customer_name
        FROM payments p
        JOIN sales s ON s.id = p.sale_id
        JOIN customers c ON c.id = s.customer_id
        WHERE DATE(p.payment_date) BETWEEN %s AND %s
        ORDER BY p.id DESC
        """,
        (start, end),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

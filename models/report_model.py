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
               s.discount, s.gst_amount, s.total_amount, s.sale_status, s.payment_status,
               IFNULL(IFNULL(NULLIF(TRIM(u.full_name), ''), u.username), '—') AS generated_by
        FROM sales s
        JOIN customers c ON c.id = s.customer_id
        LEFT JOIN users u ON u.id = s.created_by
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


def receivables_aging():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.invoice_no, s.sale_date, c.name AS customer_name,
               s.total_amount, IFNULL(s.paid_amount,0) AS paid_amount,
               (s.total_amount - IFNULL(s.paid_amount,0)) AS due,
               DATEDIFF(CURDATE(), s.sale_date) AS days_overdue,
               CASE
                 WHEN DATEDIFF(CURDATE(), s.sale_date) <= 30 THEN '0-30'
                 WHEN DATEDIFF(CURDATE(), s.sale_date) <= 60 THEN '31-60'
                 WHEN DATEDIFF(CURDATE(), s.sale_date) <= 90 THEN '61-90'
                 ELSE '90+'
               END AS bucket,
               IFNULL(IFNULL(NULLIF(TRIM(u.full_name), ''), u.username), '—') AS generated_by
        FROM sales s
        JOIN customers c ON c.id = s.customer_id
        LEFT JOIN users u ON u.id = s.created_by
        WHERE s.sale_status='Confirmed'
          AND IFNULL(s.paid_amount,0) < s.total_amount
        ORDER BY s.sale_date
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def payables_aging():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.purchase_no, p.purchase_date, v.name AS vendor_name,
               p.total_amount, IFNULL(p.paid_amount,0) AS paid_amount,
               (p.total_amount - IFNULL(p.paid_amount,0)) AS due,
               DATEDIFF(CURDATE(), p.purchase_date) AS days_overdue,
               CASE
                 WHEN DATEDIFF(CURDATE(), p.purchase_date) <= 30 THEN '0-30'
                 WHEN DATEDIFF(CURDATE(), p.purchase_date) <= 60 THEN '31-60'
                 WHEN DATEDIFF(CURDATE(), p.purchase_date) <= 90 THEN '61-90'
                 ELSE '90+'
               END AS bucket
        FROM purchases p
        JOIN vendors v ON v.id = p.vendor_id
        WHERE LOWER(p.status)='confirmed'
          AND IFNULL(p.paid_amount,0) < p.total_amount
        ORDER BY p.purchase_date
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

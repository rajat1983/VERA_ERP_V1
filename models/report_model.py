from db import get_db_connection
from utils.tenant import tid


def _dates(from_date, to_date):
    return from_date or "1970-01-01", to_date or "2099-12-31"


def sales_report(from_date, to_date):
    conn = get_db_connection()
    cur = conn.cursor()
    start, end = _dates(from_date, to_date)
    cur.execute(
        """
        SELECT CONVERT(s.invoice_no USING utf8mb4) COLLATE utf8mb4_unicode_ci AS invoice_no,
               s.sale_date,
               CONVERT(c.name USING utf8mb4) COLLATE utf8mb4_unicode_ci AS customer_name,
               s.discount, s.gst_amount, s.total_amount,
               CONVERT(s.sale_status USING utf8mb4) COLLATE utf8mb4_unicode_ci AS sale_status,
               CONVERT(s.payment_status USING utf8mb4) COLLATE utf8mb4_unicode_ci AS payment_status,
               CONVERT(IFNULL(IFNULL(NULLIF(TRIM(u.full_name), ''), u.username), '—') USING utf8mb4)
                 COLLATE utf8mb4_unicode_ci AS generated_by
        FROM sales s
        JOIN customers c ON c.id = s.customer_id AND c.tenant_id = s.tenant_id
        LEFT JOIN users u ON u.id = s.created_by
        WHERE s.tenant_id=%s AND DATE(s.sale_date) BETWEEN %s AND %s
          AND IFNULL(s.sale_status, 'Confirmed') <> 'Cancelled'
        UNION ALL
        SELECT CONVERT(ps.bill_no USING utf8mb4) COLLATE utf8mb4_unicode_ci AS invoice_no,
               ps.sale_date,
               CONVERT(IFNULL(c.name, 'Walk-in') USING utf8mb4) COLLATE utf8mb4_unicode_ci AS customer_name,
               NULL AS discount, ps.gst_amount, ps.total_amount,
               CONVERT('POS' USING utf8mb4) COLLATE utf8mb4_unicode_ci AS sale_status,
               CONVERT(ps.payment_status USING utf8mb4) COLLATE utf8mb4_unicode_ci AS payment_status,
               CONVERT(IFNULL(IFNULL(NULLIF(TRIM(u.full_name), ''), u.username), '—') USING utf8mb4)
                 COLLATE utf8mb4_unicode_ci AS generated_by
        FROM pos_sales ps
        LEFT JOIN customers c ON c.id = ps.customer_id AND c.tenant_id = ps.tenant_id
        LEFT JOIN users u ON u.id = ps.created_by
        WHERE ps.tenant_id=%s AND DATE(ps.sale_date) BETWEEN %s AND %s
        ORDER BY sale_date DESC, invoice_no DESC
        """,
        (tid(), start, end, tid(), start, end),
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
        WHERE p.tenant_id=%s AND DATE(p.purchase_date) BETWEEN %s AND %s
        ORDER BY p.id DESC
        """,
        (tid(), start, end),
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
        WHERE tenant_id=%s
        ORDER BY name
        """,
        (tid(),),
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
        WHERE tenant_id=%s AND stock_qty <= IFNULL(low_stock_threshold, reorder_level)
        ORDER BY stock_qty
        """,
        (tid(),),
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
        SELECT p.payment_date, p.amount,
               CONVERT(p.payment_mode USING utf8mb4) COLLATE utf8mb4_unicode_ci AS payment_mode,
               CONVERT(p.reference_no USING utf8mb4) COLLATE utf8mb4_unicode_ci AS reference_no,
               CONVERT(s.invoice_no USING utf8mb4) COLLATE utf8mb4_unicode_ci AS invoice_no,
               CONVERT(c.name USING utf8mb4) COLLATE utf8mb4_unicode_ci AS customer_name
        FROM payments p
        JOIN sales s ON s.id = p.sale_id
        JOIN customers c ON c.id = s.customer_id AND c.tenant_id = s.tenant_id
        WHERE s.tenant_id=%s AND DATE(p.payment_date) BETWEEN %s AND %s
        UNION ALL
        SELECT DATE(ps.sale_date) AS payment_date, pp.amount,
               CONVERT(pp.payment_mode USING utf8mb4) COLLATE utf8mb4_unicode_ci AS payment_mode,
               CONVERT('' USING utf8mb4) COLLATE utf8mb4_unicode_ci AS reference_no,
               CONVERT(ps.bill_no USING utf8mb4) COLLATE utf8mb4_unicode_ci AS invoice_no,
               CONVERT(IFNULL(c.name, 'Walk-in') USING utf8mb4) COLLATE utf8mb4_unicode_ci AS customer_name
        FROM pos_payments pp
        JOIN pos_sales ps ON ps.id = pp.pos_sale_id
        LEFT JOIN customers c ON c.id = ps.customer_id AND c.tenant_id = ps.tenant_id
        WHERE ps.tenant_id=%s AND DATE(ps.sale_date) BETWEEN %s AND %s
        ORDER BY payment_date DESC
        """,
        (tid(), start, end, tid(), start, end),
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
        JOIN customers c ON c.id = s.customer_id AND c.tenant_id = s.tenant_id
        LEFT JOIN users u ON u.id = s.created_by
        WHERE s.tenant_id=%s AND s.sale_status='Confirmed'
          AND IFNULL(s.paid_amount,0) < s.total_amount
        ORDER BY s.sale_date
        """,
        (tid(),),
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
        WHERE p.tenant_id=%s AND LOWER(p.status)='confirmed'
          AND IFNULL(p.paid_amount,0) < p.total_amount
        ORDER BY p.purchase_date
        """,
        (tid(),),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

from db import get_db_connection


def add_payment(sale_id, payment_date, amount, payment_mode, reference_no, notes):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, total_amount, paid_amount, sale_status FROM sales WHERE id=%s",
            (sale_id,),
        )
        sale = cur.fetchone()
        if not sale:
            raise ValueError("Sale not found.")
        if sale["sale_status"] == "Cancelled":
            raise ValueError("Cannot record payment for a cancelled sale.")

        amount = float(amount)
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        paid = float(sale["paid_amount"] or 0) + amount
        total = float(sale["total_amount"] or 0)
        if paid > total + 0.01:
            raise ValueError("Paid amount cannot exceed invoice total.")

        cur.execute(
            """
            INSERT INTO payments
            (sale_id, payment_date, amount, payment_mode, reference_no, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (sale_id, payment_date, amount, payment_mode, reference_no, notes),
        )

        if paid >= total - 0.01:
            status = "Paid"
        else:
            status = "Partial"

        cur.execute(
            "UPDATE sales SET paid_amount=%s, payment_status=%s WHERE id=%s",
            (paid, status, sale_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_payments(sale_id=None):
    conn = get_db_connection()
    cur = conn.cursor()
    if sale_id:
        cur.execute(
            """
            SELECT p.*, s.invoice_no, c.name AS customer_name
            FROM payments p
            JOIN sales s ON s.id = p.sale_id
            JOIN customers c ON c.id = s.customer_id
            WHERE p.sale_id=%s
            ORDER BY p.id DESC
            """,
            (sale_id,),
        )
    else:
        cur.execute(
            """
            SELECT p.*, s.invoice_no, c.name AS customer_name
            FROM payments p
            JOIN sales s ON s.id = p.sale_id
            JOIN customers c ON c.id = s.customer_id
            ORDER BY p.id DESC
            LIMIT 200
            """
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_unpaid_sales():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.id, s.invoice_no, s.total_amount, s.paid_amount, s.payment_status, c.name AS customer_name
        FROM sales s
        JOIN customers c ON c.id = s.customer_id
        WHERE s.sale_status='Confirmed'
          AND IFNULL(s.paid_amount,0) < s.total_amount
        ORDER BY s.id DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def add_vendor_payment(purchase_id, payment_date, amount, payment_mode, reference_no, notes):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, total_amount, IFNULL(paid_amount,0) AS paid_amount, status FROM purchases WHERE id=%s",
            (purchase_id,),
        )
        purchase = cur.fetchone()
        if not purchase:
            raise ValueError("Purchase not found.")
        if str(purchase["status"]).lower() == "cancelled":
            raise ValueError("Cannot record payment for a cancelled purchase.")
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        paid = float(purchase["paid_amount"] or 0) + amount
        total = float(purchase["total_amount"] or 0)
        if paid > total + 0.01:
            raise ValueError("Paid amount cannot exceed purchase total.")
        cur.execute(
            """
            INSERT INTO vendor_payments
            (purchase_id, payment_date, amount, payment_mode, reference_no, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (purchase_id, payment_date, amount, payment_mode, reference_no, notes),
        )
        status = "Paid" if paid >= total - 0.01 else "Partial"
        cur.execute(
            "UPDATE purchases SET paid_amount=%s, payment_status=%s WHERE id=%s",
            (paid, status, purchase_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_vendor_payments():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT vp.*, p.purchase_no, v.name AS vendor_name
        FROM vendor_payments vp
        JOIN purchases p ON p.id = vp.purchase_id
        JOIN vendors v ON v.id = p.vendor_id
        ORDER BY vp.id DESC
        LIMIT 200
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_unpaid_purchases():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.id, p.purchase_no, p.total_amount, IFNULL(p.paid_amount,0) AS paid_amount,
               p.payment_status, v.name AS vendor_name
        FROM purchases p
        JOIN vendors v ON v.id = p.vendor_id
        WHERE LOWER(p.status) = 'confirmed'
          AND IFNULL(p.paid_amount,0) < p.total_amount
        ORDER BY p.id DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def payables_outstanding():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT IFNULL(SUM(total_amount - IFNULL(paid_amount,0)), 0) AS outstanding
        FROM purchases
        WHERE LOWER(status)='confirmed'
          AND IFNULL(paid_amount,0) < total_amount
        """
    )
    total = float(cur.fetchone()["outstanding"])
    cur.close()
    conn.close()
    return total

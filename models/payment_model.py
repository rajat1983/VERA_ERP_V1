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

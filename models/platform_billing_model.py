from datetime import datetime

from db import get_db_connection
from models import subscription_model
from utils.razorpay import quote_plan


def _next_invoice_no(cur):
    year = datetime.now().strftime("%Y")
    lock_name = f"vera_platform_inv_{year}"
    cur.execute("SELECT GET_LOCK(%s, 10) AS locked", (lock_name,))
    lock = cur.fetchone()
    if not lock or not int(lock["locked"]):
        raise ValueError("Could not allocate a platform invoice number.")
    cur.execute(
        """
        SELECT invoice_no FROM platform_invoices
        WHERE invoice_no LIKE %s
        ORDER BY invoice_no DESC
        LIMIT 1
        FOR UPDATE
        """,
        (f"PL{year}%",),
    )
    row = cur.fetchone()
    seq = int(str(row["invoice_no"])[-5:]) + 1 if row and row["invoice_no"] else 1
    return f"PL{year}{seq:05d}", lock_name


def list_for_tenant(tenant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT i.invoice_no, i.total_paise, i.gst_paise, i.created_at,
                   p.gateway, p.gateway_payment_id, p.status
            FROM platform_invoices i
            LEFT JOIN platform_payments p ON p.invoice_id = i.id
            WHERE i.tenant_id=%s
            ORDER BY i.id DESC
            LIMIT 50
            """,
            (tenant_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def fulfill(tenant_id, plan, payment_id, order_id, amount_paise, source="razorpay"):
    if not payment_id:
        raise ValueError("Missing payment id.")
    ex, gst, total = quote_plan(plan)
    if int(amount_paise or 0) < total:
        raise ValueError("Paid amount is less than the plan total.")
    conn = get_db_connection()
    cur = conn.cursor()
    lock_name = None
    try:
        cur.execute(
            "SELECT id, invoice_id FROM platform_payments WHERE gateway_payment_id=%s",
            (payment_id,),
        )
        existing = cur.fetchone()
        if existing:
            return {"duplicate": True, "invoice_id": existing.get("invoice_id")}
        invoice_no, lock_name = _next_invoice_no(cur)
        cur.execute(
            """
            INSERT INTO platform_invoices
            (tenant_id, invoice_no, plan_id, amount_ex_paise, gst_paise, total_paise, gst_rate)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (tenant_id, invoice_no, plan["id"], ex, gst, total, plan["gst_rate"]),
        )
        invoice_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO platform_payments
            (tenant_id, invoice_id, gateway, gateway_order_id, gateway_payment_id, amount_paise, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'captured')
            """,
            (tenant_id, invoice_id, source, order_id, payment_id, total),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if lock_name:
            try:
                cur.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
            except Exception:
                pass
        cur.close()
        conn.close()
    subscription_model.apply_paid(tenant_id, plan["id"], note=f"{source} {payment_id}")
    return {"duplicate": False, "invoice_no": invoice_no, "invoice_id": invoice_id}

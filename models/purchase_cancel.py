from db import get_db_connection
from utils.ownership import bump_stock, record_movement
from utils.tenant import tid


def cancel_purchase(purchase_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT status FROM purchases WHERE id=%s AND tenant_id=%s FOR UPDATE",
            (purchase_id, tid()),
        )
        purchase = cur.fetchone()
        if not purchase:
            raise ValueError("Purchase not found.")
        if str(purchase["status"]).lower() == "cancelled":
            raise ValueError("Purchase is already cancelled.")

        cur.execute(
            """
            UPDATE purchases SET status='cancelled'
            WHERE id=%s AND tenant_id=%s AND LOWER(status) <> 'cancelled'
            """,
            (purchase_id, tid()),
        )
        if cur.rowcount == 0:
            raise ValueError("Purchase is already cancelled.")

        cur.execute(
            "SELECT product_id, quantity FROM purchase_items WHERE purchase_id=%s AND tenant_id=%s",
            (purchase_id, tid()),
        )
        items = cur.fetchall()
        for item in items:
            bump_stock(cur, item["product_id"], -item["quantity"])
            record_movement(
                cur,
                item["product_id"],
                "adjustment",
                -item["quantity"],
                purchase_id,
                "purchase_cancel",
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

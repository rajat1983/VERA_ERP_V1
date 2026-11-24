from db import get_db_connection
from utils.tenant import tid


def cancel_purchase(purchase_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT status FROM purchases WHERE id=%s AND tenant_id=%s", (purchase_id, tid()))
        purchase = cur.fetchone()
        if not purchase:
            raise ValueError("Purchase not found.")
        if str(purchase["status"]).lower() == "cancelled":
            raise ValueError("Purchase is already cancelled.")

        cur.execute(
            "SELECT product_id, quantity FROM purchase_items WHERE purchase_id=%s",
            (purchase_id,),
        )
        items = cur.fetchall()
        for item in items:
            cur.execute(
                """
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id = %s AND stock_qty >= %s
                """,
                (item["quantity"], item["product_id"], item["quantity"]),
            )
            if cur.rowcount == 0:
                raise ValueError(
                    f"Cannot reverse stock for product {item['product_id']}."
                )
            cur.execute(
                """
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, reference_id, reference_type)
                VALUES (%s, 'adjustment', %s, %s, 'purchase_cancel')
                """,
                (item["product_id"], -item["quantity"], purchase_id),
            )

        cur.execute(
            "UPDATE purchases SET status='cancelled' WHERE id=%s",
            (purchase_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

from db import get_db_connection


def get_all_batches():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.*, p.name AS product_name
        FROM production_batches b
        JOIN products p ON p.id = b.product_id
        ORDER BY b.id DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def cancel_production(batch_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM production_batches WHERE id=%s", (batch_id,))
        batch = cur.fetchone()
        if not batch:
            raise ValueError("Batch not found.")
        if str(batch.get("status") or "").lower() == "cancelled":
            raise ValueError("Batch is already cancelled.")

        cur.execute(
            "SELECT raw_material_id, quantity_used FROM production_materials WHERE batch_id=%s",
            (batch_id,),
        )
        materials = cur.fetchall()
        for m in materials:
            cur.execute(
                "UPDATE products SET stock_qty = stock_qty + %s WHERE id=%s",
                (m["quantity_used"], m["raw_material_id"]),
            )
            cur.execute(
                """
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, reference_id, reference_type)
                VALUES (%s,'adjustment',%s,%s,'production_cancel')
                """,
                (m["raw_material_id"], m["quantity_used"], batch_id),
            )

        cur.execute(
            """
            UPDATE products SET stock_qty = stock_qty - %s
            WHERE id=%s AND stock_qty >= %s
            """,
            (batch["quantity_produced"], batch["product_id"], batch["quantity_produced"]),
        )
        if cur.rowcount == 0:
            raise ValueError("Cannot reverse finished-goods stock.")
        cur.execute(
            """
            INSERT INTO stock_movements
            (product_id, movement_type, quantity, reference_id, reference_type)
            VALUES (%s,'adjustment',%s,%s,'production_cancel')
            """,
            (batch["product_id"], -batch["quantity_produced"], batch_id),
        )
        cur.execute(
            "UPDATE production_batches SET status='cancelled' WHERE id=%s",
            (batch_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

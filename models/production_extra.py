from db import get_db_connection
from utils.ownership import bump_stock, record_movement, require_product
from utils.tenant import tid


def get_all_batches():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.*, p.name AS product_name
        FROM production_batches b
        JOIN products p ON p.id = b.product_id AND p.tenant_id = b.tenant_id
        WHERE b.tenant_id=%s
        ORDER BY b.id DESC
        """,
        (tid(),),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def cancel_production(batch_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT * FROM production_batches WHERE id=%s AND tenant_id=%s FOR UPDATE",
            (batch_id, tid()),
        )
        batch = cur.fetchone()
        if not batch:
            raise ValueError("Batch not found.")
        if str(batch.get("status") or "").lower() == "cancelled":
            raise ValueError("Batch is already cancelled.")

        cur.execute(
            """
            UPDATE production_batches SET status='cancelled'
            WHERE id=%s AND tenant_id=%s AND LOWER(IFNULL(status,'confirmed')) <> 'cancelled'
            """,
            (batch_id, tid()),
        )
        if cur.rowcount == 0:
            raise ValueError("Batch is already cancelled.")

        cur.execute(
            """
            SELECT raw_material_id, quantity_used
            FROM production_materials
            WHERE batch_id=%s AND tenant_id=%s
            """,
            (batch_id, tid()),
        )
        materials = cur.fetchall()
        for m in materials:
            require_product(cur, m["raw_material_id"])
            bump_stock(cur, m["raw_material_id"], m["quantity_used"])
            record_movement(
                cur,
                m["raw_material_id"],
                "adjustment",
                m["quantity_used"],
                batch_id,
                "production_cancel",
            )

        require_product(cur, batch["product_id"])
        bump_stock(cur, batch["product_id"], -batch["quantity_produced"])
        record_movement(
            cur,
            batch["product_id"],
            "adjustment",
            -batch["quantity_produced"],
            batch_id,
            "production_cancel",
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

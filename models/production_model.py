from db import get_db_connection
from utils.tenant import tid
from datetime import datetime, timedelta


def generate_batch_code():

    today = datetime.today().strftime("%y%m%d")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS count
        FROM production_batches
        WHERE tenant_id=%s AND DATE(created_at)=CURDATE()
    """, (tid(),))

    count = cur.fetchone()["count"] + 1

    cur.close()
    conn.close()

    return f"VERA-{today}-{str(count).zfill(2)}"


def get_recipes(product_id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM product_recipes
        WHERE finished_product_id = %s
    """, (product_id,))

    recipes = cur.fetchall()

    cur.close()
    conn.close()

    return recipes


def create_production(product_id, quantity, wastage, batch_date):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        batch_code = generate_batch_code()

        expiry_date = datetime.strptime(batch_date, "%Y-%m-%d") + timedelta(days=180)

        recipes = get_recipes(product_id)

        # Check stock first
        for r in recipes:

            required_qty = r["quantity_required"] * quantity

            cur.execute("""
                SELECT stock_qty
                FROM products
                WHERE id=%s
            """, (r["raw_material_id"],))

            stock = cur.fetchone()["stock_qty"]

            if stock < required_qty:
                raise ValueError("Insufficient stock for raw material ID " + str(r["raw_material_id"]))

        # Create batch
        cur.execute("""
            INSERT INTO production_batches
            (tenant_id, batch_code, product_id, quantity_produced, wastage, batch_date, expiry_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            tid(),
            batch_code,
            product_id,
            quantity,
            wastage,
            batch_date,
            expiry_date
        ))

        batch_id = cur.lastrowid

        # Deduct raw materials
        for r in recipes:

            used_qty = r["quantity_required"] * quantity

            cur.execute("""
                INSERT INTO production_materials
                (tenant_id, batch_id, raw_material_id, quantity_used)
                VALUES (%s,%s,%s,%s)
            """, (
                tid(),
                batch_id,
                r["raw_material_id"],
                used_qty
            ))

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id=%s
            """, (
                used_qty,
                r["raw_material_id"]
            ))

            cur.execute("""
                INSERT INTO stock_movements
                (tenant_id, product_id, movement_type, quantity, reference_id, reference_type)
                VALUES (%s,%s,'production_out',-%s,%s,'production')
            """, (
                tid(),
                r["raw_material_id"],
                used_qty,
                batch_id
            ))

        # Increase finished goods
        cur.execute("""
            UPDATE products
            SET stock_qty = stock_qty + %s
            WHERE id=%s
        """, (
            quantity,
            product_id
        ))

        cur.execute("""
            INSERT INTO stock_movements
            (tenant_id, product_id, movement_type, quantity, reference_id, reference_type)
            VALUES (%s,%s,'production_in',%s,%s,'production')
        """, (
            tid(),
            product_id,
            quantity,
            batch_id
        ))

        conn.commit()

        return batch_id

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        cur.close()
        conn.close()
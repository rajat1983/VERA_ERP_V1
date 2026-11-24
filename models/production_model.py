from datetime import datetime, timedelta

from db import get_db_connection
from utils.ownership import bump_stock, record_movement, require_product
from utils.tenant import tid


def generate_batch_code():

    today = datetime.today().strftime("%y%m%d")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM production_batches
        WHERE tenant_id=%s AND DATE(created_at)=CURDATE()
        """,
        (tid(),),
    )

    count = cur.fetchone()["count"] + 1

    cur.close()
    conn.close()

    return f"VERA-{today}-{str(count).zfill(2)}"


def get_recipes(product_id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM product_recipes
        WHERE finished_product_id = %s AND tenant_id = %s
        """,
        (product_id, tid()),
    )

    recipes = cur.fetchall()

    cur.close()
    conn.close()

    return recipes


def create_production(product_id, quantity, wastage, batch_date):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        finished = require_product(cur, product_id)
        batch_code = generate_batch_code()

        expiry_date = datetime.strptime(batch_date, "%Y-%m-%d") + timedelta(days=180)

        recipes = get_recipes(product_id)

        for r in recipes:
            require_product(cur, r["raw_material_id"])
            required_qty = r["quantity_required"] * quantity
            cur.execute(
                """
                SELECT stock_qty
                FROM products
                WHERE id=%s AND tenant_id=%s
                FOR UPDATE
                """,
                (r["raw_material_id"], tid()),
            )
            stock = cur.fetchone()["stock_qty"]
            if stock < required_qty:
                raise ValueError("Insufficient stock for raw material ID " + str(r["raw_material_id"]))

        cur.execute(
            """
            INSERT INTO production_batches
            (tenant_id, batch_code, product_id, quantity_produced, wastage, batch_date, expiry_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                tid(),
                batch_code,
                finished["id"],
                quantity,
                wastage,
                batch_date,
                expiry_date,
            ),
        )

        batch_id = cur.lastrowid

        for r in recipes:
            used_qty = r["quantity_required"] * quantity
            cur.execute(
                """
                INSERT INTO production_materials
                (tenant_id, batch_id, raw_material_id, quantity_used)
                VALUES (%s,%s,%s,%s)
                """,
                (tid(), batch_id, r["raw_material_id"], used_qty),
            )
            bump_stock(cur, r["raw_material_id"], -used_qty)
            record_movement(
                cur, r["raw_material_id"], "production_out", -used_qty, batch_id, "production"
            )

        bump_stock(cur, finished["id"], quantity)
        record_movement(cur, finished["id"], "production_in", quantity, batch_id, "production")

        conn.commit()

        return batch_id

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        cur.close()
        conn.close()

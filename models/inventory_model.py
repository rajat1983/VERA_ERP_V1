from db import get_db_connection


def get_movements(search="", limit=50, offset=0):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"
    cur.execute(
        """
        SELECT m.*, p.name AS product_name, p.sku
        FROM stock_movements m
        JOIN products p ON p.id = m.product_id
        WHERE p.name LIKE %s OR p.sku LIKE %s OR m.movement_type LIKE %s
        ORDER BY m.id DESC
        LIMIT %s OFFSET %s
        """,
        (like, like, like, limit, offset),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_movement_count(search=""):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"
    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM stock_movements m
        JOIN products p ON p.id = m.product_id
        WHERE p.name LIKE %s OR p.sku LIKE %s OR m.movement_type LIKE %s
        """,
        (like, like, like),
    )
    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total


def get_stock_on_hand(search=""):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"
    cur.execute(
        """
        SELECT
            id,
            sku,
            name,
            stock_qty,
            reorder_level,
            IFNULL(low_stock_threshold, reorder_level) AS threshold,
            cost_price,
            selling_price,
            status,
            (IFNULL(stock_qty, 0) * IFNULL(cost_price, 0)) AS stock_value
        FROM products
        WHERE name LIKE %s OR sku LIKE %s
        ORDER BY name
        """,
        (like, like),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_low_stock(search=""):
    rows = get_stock_on_hand(search)
    return [r for r in rows if (r.get("stock_qty") or 0) <= (r.get("threshold") or 0)]


def adjust_stock(product_id, direction, quantity, reason):
    quantity = int(quantity)
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if direction not in ("in", "out"):
        raise ValueError("Direction must be in or out.")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Reason is required.")

    delta = quantity if direction == "in" else -quantity
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id, name, stock_qty FROM products WHERE id=%s FOR UPDATE",
            (product_id,),
        )
        product = cur.fetchone()
        if not product:
            raise ValueError("Product not found.")
        new_qty = int(product["stock_qty"] or 0) + delta
        if new_qty < 0:
            raise ValueError("Adjustment would make stock negative.")
        cur.execute("UPDATE products SET stock_qty=%s WHERE id=%s", (new_qty, product_id))
        cur.execute(
            """
            INSERT INTO stock_movements
            (product_id, movement_type, quantity, reference_id, reference_type, remarks)
            VALUES (%s, 'adjustment', %s, %s, 'adjustment', %s)
            """,
            (product_id, delta, product_id, reason[:255]),
        )
        conn.commit()
        return new_qty
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

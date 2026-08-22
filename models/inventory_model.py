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

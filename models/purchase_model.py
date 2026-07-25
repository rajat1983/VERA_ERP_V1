from db import get_db_connection

def create_purchase(vendor_id, invoice_no, purchase_date, items):

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        subtotal = 0

        # Insert purchase (draft first)
        cur.execute("""
            INSERT INTO purchases(vendor_id, invoice_no, purchase_date)
            VALUES (%s,%s,%s)
        """, (vendor_id, invoice_no, purchase_date))

        purchase_id = cur.lastrowid

        for item in items:
            line_total = item["qty"] * item["price"]
            subtotal += line_total

            cur.execute("""
                INSERT INTO purchase_items
                (purchase_id, product_id, quantity, price, line_total)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                purchase_id,
                item["product_id"],
                item["qty"],
                item["price"],
                line_total
            ))

        cur.execute("""
            UPDATE purchases
            SET subtotal=%s, total_amount=%s, status='confirmed'
            WHERE id=%s
        """, (subtotal, subtotal, purchase_id))

        # 🔥 STOCK UPDATE
        for item in items:
            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty + %s
                WHERE id=%s
            """, (item["qty"], item["product_id"]))

            cur.execute("""
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, reference_id, reference_type)
                VALUES (%s,'purchase',%s,%s,'purchase')
            """, (item["product_id"], item["qty"], purchase_id))

        conn.commit()
        return purchase_id

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()

def get_all_purchases():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.*,
               v.name AS vendor_name
        FROM purchases p
        JOIN vendors v ON p.vendor_id = v.id
        ORDER BY p.id DESC
    """)

    purchases = cur.fetchall()

    cur.close()
    conn.close()

    return purchases
def get_purchase_by_id(purchase_id):

    conn = get_db_connection()
    cur = conn.cursor()

    # Purchase Header
    cur.execute("""
        SELECT p.*, v.name AS vendor_name
        FROM purchases p
        JOIN vendors v ON p.vendor_id = v.id
        WHERE p.id = %s
    """, (purchase_id,))

    purchase = cur.fetchone()

    # Purchase Items
    cur.execute("""
        SELECT pi.*, pr.name AS product_name
        FROM purchase_items pi
        JOIN products pr ON pi.product_id = pr.id
        WHERE pi.purchase_id = %s
    """, (purchase_id,))

    items = cur.fetchall()

    cur.close()
    conn.close()

    return purchase, items
def delete_purchase(purchase_id):

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 1️⃣ Get items
        cur.execute("""
            SELECT product_id, quantity
            FROM purchase_items
            WHERE purchase_id = %s
        """, (purchase_id,))

        items = cur.fetchall()

        # 2️⃣ Reverse stock
        for item in items:

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id = %s
            """, (item["quantity"], item["product_id"]))

            cur.execute("""
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, reference_id, reference_type)
                VALUES (%s,'adjustment',-%s,%s,'purchase_delete')
            """, (
                item["product_id"],
                item["quantity"],
                purchase_id
            ))

        # 3️⃣ Delete items
        cur.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))

        # 4️⃣ Delete purchase
        cur.execute("DELETE FROM purchases WHERE id = %s", (purchase_id,))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()
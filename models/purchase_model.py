from db import get_db_connection
from utils.totals import calculate_document_totals

def create_purchase(
    purchase_no,
    vendor_id,
    vendor_invoice_no,
    purchase_date,
    items,
    discount=0
):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        for item in items:
            cur.execute(
                "SELECT tax_rate FROM products WHERE id=%s",
                (item["product_id"],),
            )
            prod = cur.fetchone()
            item["tax_rate"] = float(prod["tax_rate"] if prod else 0)

        totals = calculate_document_totals(items, discount)

        cur.execute("""
            INSERT INTO purchases
            (
                purchase_no,
                vendor_id,
                vendor_invoice_no,
                purchase_date,
                discount,
                discount_amount,
                gst_amount,
                subtotal,
                total_amount,
                status
            )
            VALUES
            (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmed'
            )
        """, (
            purchase_no,
            vendor_id,
            vendor_invoice_no,
            purchase_date,
            totals["discount_percent"],
            totals["discount_amount"],
            totals["gst_amount"],
            totals["subtotal"],
            totals["grand_total"]
        ))

        purchase_id = cur.lastrowid

        for item in items:

            cur.execute("""
                INSERT INTO purchase_items
                (
                    purchase_id,
                    product_id,
                    quantity,
                    price,
                    line_total
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                purchase_id,
                item["product_id"],
                item["qty"],
                item["price"],
                item["line_total"]
            ))

        # Update Stock
        for item in items:

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty + %s
                WHERE id=%s
            """, (
                item["qty"],
                item["product_id"]
            ))

            cur.execute("""
                INSERT INTO stock_movements
                (
                    product_id,
                    movement_type,
                    quantity,
                    reference_id,
                    reference_type
                )
                VALUES
                (
                    %s,
                    'purchase',
                    %s,
                    %s,
                    'purchase'
                )
            """, (
                item["product_id"],
                item["qty"],
                purchase_id
            ))

        conn.commit()

        return purchase_id

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        cur.close()
        conn.close()

def get_all_purchases(search="", limit=10, offset=0):

    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT p.*,
               v.name AS vendor_name
        FROM purchases p
        JOIN vendors v ON p.vendor_id = v.id
        WHERE p.purchase_no LIKE %s
           OR p.vendor_invoice_no LIKE %s
           OR v.name LIKE %s
        ORDER BY p.id DESC
        LIMIT %s OFFSET %s
    """, (like, like, like, limit, offset))

    purchases = cur.fetchall()

    cur.close()
    conn.close()

    return purchases


def get_purchase_count(search=""):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM purchases p
        JOIN vendors v ON p.vendor_id = v.id
        WHERE p.purchase_no LIKE %s
           OR p.vendor_invoice_no LIKE %s
           OR v.name LIKE %s
    """, (like, like, like))
    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total


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
def generate_purchase_number():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT MAX(id) AS last_id
        FROM purchases
    """)

    row = cur.fetchone()

    next_id = 1

    if row and row["last_id"]:
        next_id = row["last_id"] + 1

    purchase_no = f"PUR{next_id:06d}"

    cur.close()
    conn.close()

    return purchase_no
# ==========================================
# Check Duplicate Vendor Invoice
# ==========================================

def purchase_invoice_exists(
    vendor_id,
    vendor_invoice_no,
    exclude_purchase_id=None
):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        query = """
            SELECT id
            FROM purchases
            WHERE vendor_id = %s
              AND vendor_invoice_no = %s
        """

        params = [
            vendor_id,
            vendor_invoice_no
        ]

        # Ignore current purchase while editing
        if exclude_purchase_id is not None:

            query += " AND id <> %s"

            params.append(exclude_purchase_id)

        query += " LIMIT 1"

        cur.execute(
            query,
            tuple(params)
        )

        purchase = cur.fetchone()

        return purchase is not None

    finally:

        cur.close()
        conn.close()
        
def update_purchase(
    purchase_id,
    vendor_id,
    vendor_invoice_no,
    purchase_date,
    items,
    discount=0
):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute("SELECT status FROM purchases WHERE id=%s", (purchase_id,))
        existing = cur.fetchone()
        if not existing:
            raise ValueError("Purchase not found.")
        if str(existing["status"]).lower() == "cancelled":
            raise ValueError("Cancelled purchase cannot be edited.")

        subtotal = 0

        # -----------------------------------------
        # Reverse Previous Stock
        # -----------------------------------------

        cur.execute("""
            SELECT
                product_id,
                quantity
            FROM purchase_items
            WHERE purchase_id = %s
        """, (purchase_id,))

        old_items = cur.fetchall()

        for item in old_items:

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id = %s
            """, (
                item["quantity"],
                item["product_id"]
            ))

        # -----------------------------------------
        # Delete Old Purchase Items
        # -----------------------------------------

        cur.execute("""
            DELETE
            FROM purchase_items
            WHERE purchase_id = %s
        """, (purchase_id,))
                # -----------------------------------------
        # Update Purchase Header
        # -----------------------------------------

        cur.execute("""
            UPDATE purchases
            SET
                vendor_id = %s,
                vendor_invoice_no = %s,
                purchase_date = %s
            WHERE id = %s
        """, (
            vendor_id,
            vendor_invoice_no,
            purchase_date,
            purchase_id
        ))

        # -----------------------------------------
        # Insert Updated Purchase Items
        # -----------------------------------------

        for item in items:

            line_total = item["qty"] * item["price"]

            item["line_total"] = line_total

            cur.execute(
                "SELECT tax_rate FROM products WHERE id=%s",
                (item["product_id"],),
            )
            prod = cur.fetchone()
            item["tax_rate"] = float(prod["tax_rate"] if prod else 0)

            cur.execute("""
                INSERT INTO purchase_items
                (
                    purchase_id,
                    product_id,
                    quantity,
                    price,
                    line_total
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                purchase_id,
                item["product_id"],
                item["qty"],
                item["price"],
                item["line_total"]
            ))

            # -----------------------------------------
            # Increase Stock Again
            # -----------------------------------------

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty + %s
                WHERE id = %s
            """, (
                item["qty"],
                item["product_id"]
            ))

            # -----------------------------------------
            # Stock Movement
            # -----------------------------------------

            cur.execute("""
                INSERT INTO stock_movements
                (
                    product_id,
                    movement_type,
                    quantity,
                    reference_id,
                    reference_type
                )
                VALUES
                (
                    %s,
                    'purchase_edit',
                    %s,
                    %s,
                    'purchase'
                )
            """, (
                item["product_id"],
                item["qty"],
                purchase_id
            ))

        # -----------------------------------------
        # Update Purchase Total
        # -----------------------------------------

        totals = calculate_document_totals(items, discount)

        cur.execute("""
            UPDATE purchases
            SET
                subtotal = %s,
                discount = %s,
                discount_amount = %s,
                gst_amount = %s,
                total_amount = %s
            WHERE id = %s
        """, (
            totals["subtotal"],
            totals["discount_percent"],
            totals["discount_amount"],
            totals["gst_amount"],
            totals["grand_total"],
            purchase_id
        ))

        conn.commit()

        return True

    except Exception as e:

        conn.rollback()
        raise e

    finally:

        cur.close()
        conn.close()
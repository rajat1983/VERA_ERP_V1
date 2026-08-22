import pymysql
from db import get_db_connection
from datetime import datetime
from models.product_model import reduce_stock, increase_stock

def get_next_invoice_number():
    year = datetime.now().strftime("%Y")

    conn = get_db_connection()
    cur = conn.cursor()

    # Get latest invoice for this year
    cur.execute("""
        SELECT invoice_no 
        FROM sales 
        WHERE invoice_no LIKE %s
        ORDER BY invoice_no DESC 
        LIMIT 1
    """, (year + "%",))

    row = cur.fetchone()

    if row:
        last_invoice = row["invoice_no"]
        # Extract last 5 digits
        last_seq = int(last_invoice[-5:])
        next_seq = last_seq + 1
    else:
        next_seq = 1   # First invoice of the year

    next_invoice = f"{year}{next_seq:05d}"

    cur.close()
    conn.close()

    return next_invoice
def get_all_sales(search, limit, offset):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT s.id,
                s.invoice_no,
                s.sale_status,
               s.sale_date,
                s.total_amount,
                s.discount,
                c.name AS customer_name
         FROM sales s
         JOIN customers c ON s.customer_id = c.id
         ORDER BY s.id DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def create_sale(invoice_no, customer_id, sale_date, remarks, discount, items):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        total = 0
        # ==========================================
        # Validate Duplicate Products
        # ==========================================

        product_ids = set()

        for item in items:

            product_id = str(item["product_id"])

            if product_id in product_ids:
                raise ValueError(
                    "Same product cannot be added more than once "
                    "in the same invoice."
                )

            product_ids.add(product_id)

        # ==========================================
        # 1. Validate Stock Before Creating Sale
        # ==========================================

        for item in items:

            if not check_stock(
                item["product_id"],
                item["qty"]
            ):

                product = get_product(
                    item["product_id"]
                )

                pname = (
                    product["name"]
                    if product
                    else f"Product ID {item['product_id']}"
                )

                raise ValueError(
                    f"Not enough stock for '{pname}'. "
                    f"Requested Qty: {item['qty']}"
                )

        # ==========================================
        # 2. Calculate Subtotal
        # ==========================================

        for item in items:

            line_total = (
                item["qty"] *
                item["price"]
            )

            total += line_total

        # ==========================================
        # 3. Validate Discount Percentage
        # ==========================================

        discount_percent = float(discount)

        if discount_percent < 0 or discount_percent > 100:
            raise ValueError(
                "Discount must be between 0% and 100%."
            )

        # ==========================================
        # 4. Calculate Discount Amount
        # ==========================================

        discount_amount = (
            total * discount_percent
        ) / 100

        # ==========================================
        # 5. Calculate Grand Total
        # ==========================================

        grand_total = (
            total - discount_amount
        )

        # ==========================================
        # 6. Insert Sale Header
        # ==========================================

        cur.execute("""
            INSERT INTO sales
            (
                invoice_no,
                customer_id,
                sale_date,
                remarks,
                discount,
                total_amount
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            invoice_no,
            customer_id,
            sale_date,
            remarks,
            discount_percent,
            grand_total
        ))

        sale_id = cur.lastrowid

        # ==========================================
        # 7. Insert Sale Items
        #    + Reduce Stock
        #    + Stock Movement
        # ==========================================

        for item in items:

            line_total = (
                item["qty"] *
                item["price"]
            )

            # ------------------------------------------
            # Insert Sale Item
            # ------------------------------------------

            cur.execute("""
                INSERT INTO sale_items
                (
                    sale_id,
                    product_id,
                    qty,
                    price,
                    line_total
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                sale_id,
                item["product_id"],
                item["qty"],
                item["price"],
                line_total
            ))

            # ------------------------------------------
            # Reduce Product Stock
            # ------------------------------------------

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id = %s
                  AND stock_qty >= %s
            """, (
                item["qty"],
                item["product_id"],
                item["qty"]
            ))

            if cur.rowcount == 0:
                raise ValueError(
                    f"Insufficient stock for "
                    f"Product ID {item['product_id']}."
                )

            # ------------------------------------------
            # Stock Movement
            # ------------------------------------------

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
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                item["product_id"],
                -item["qty"],
                sale_id
            ))

        # ==========================================
        # 8. Commit
        # ==========================================

        conn.commit()

        return sale_id

    except Exception:

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()

def get_product(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM products WHERE id=%s       
    """, (id))
    pname = cur.fetchone()
    cur.close()
    conn.close()
    return pname


def get_sale_by_id(sale_id):

    conn = get_db_connection()
    cur = conn.cursor()

    # ============================
    # Sale Header
    # ============================

    cur.execute("""
        SELECT
            s.*,
            c.name AS customer_name,
            c.address,
            c.phone,
            c.email
        FROM sales s
        JOIN customers c
            ON s.customer_id = c.id
        WHERE s.id = %s
    """, (sale_id,))

    sale = cur.fetchone()

    # ============================
    # Sale Items
    # ============================

    cur.execute("""
        SELECT
            si.*,
            p.name AS product_name
        FROM sale_items si
        JOIN products p
            ON si.product_id = p.id
        WHERE si.sale_id = %s
    """, (sale_id,))

    items = cur.fetchall()

    cur.close()
    conn.close()

    return sale, items

def get_sale_items(sale_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT si.*, p.name AS product_name
        FROM sale_items si
        JOIN products p ON p.id = si.product_id
        WHERE sale_id=%s
    """, (sale_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

from db import get_db_connection
def update_sale(sale_id, customer_id, discount, total_amount, items):

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # ==========================================
        # Validate Duplicate Products
        # ==========================================

        product_ids = set()

        for item in items:

            product_id = str(item["product_id"])

            if product_id in product_ids:
                raise ValueError(
                    "Same product cannot be added more than once "
                    "in the same invoice."
                )

            product_ids.add(product_id)

        # ==========================================
        # 1. Get Existing Sale Items
        # ==========================================

        cur.execute("""
            SELECT product_id, qty
            FROM sale_items
            WHERE sale_id = %s
        """, (sale_id,))

        old_items = cur.fetchall()

        # ==========================================
        # 2. Restore Old Stock
        # ==========================================

        for item in old_items:

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty + %s
                WHERE id = %s
            """, (
                item["qty"],
                item["product_id"]
            ))

            if cur.rowcount == 0:
                raise ValueError(
                    f"Unable to restore stock for "
                    f"Product ID {item['product_id']}"
                )

            # Stock Movement - Reverse Old Sale
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
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                item["product_id"],
                item["qty"],
                sale_id
            ))

        # ==========================================
        # 3. Remove Existing Sale Items
        # ==========================================

        cur.execute("""
            DELETE FROM sale_items
            WHERE sale_id = %s
        """, (sale_id,))

        # ==========================================
        # 4. Update Sale Header
        # ==========================================

        cur.execute("""
            UPDATE sales
            SET customer_id = %s,
                discount = %s,
                total_amount = %s
            WHERE id = %s
        """, (
            customer_id,
            discount,
            total_amount,
            sale_id
        ))

        if cur.rowcount == 0:
            cur.execute("""
                SELECT invoice_no
                FROM sales
                WHERE id = %s
            """, (sale_id,))

            sale = cur.fetchone()

            invoice_no = (
                sale["invoice_no"]
                if sale
                else f"#{sale_id}"
            )

            raise ValueError(
                f"Invoice {invoice_no} could not be updated."
            )

        # ==========================================
        # 5. Insert New Sale Items
        #    + Reduce Stock
        # ==========================================

        for item in items:

            # Reduce stock atomically
            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id = %s
                  AND stock_qty >= %s
            """, (
                item["qty"],
                item["product_id"],
                item["qty"]
            ))

            if cur.rowcount == 0:
                raise ValueError(
                    f"Insufficient stock for "
                    f"Product ID {item['product_id']}."
                )

            # Insert Sale Item
            cur.execute("""
                INSERT INTO sale_items
                (
                    sale_id,
                    product_id,
                    qty,
                    price,
                    line_total
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                sale_id,
                item["product_id"],
                item["qty"],
                item["price"],
                item["line_total"]
            ))

            # Stock Movement - New Sale Quantity
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
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                item["product_id"],
                -item["qty"],
                sale_id
            ))

        # ==========================================
        # 6. Commit Everything
        # ==========================================

        conn.commit()

    except Exception:

        # ==========================================
        # Rollback Everything
        # ==========================================

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()

def get_sale_count(search):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM sales
        WHERE invoice_no LIKE %s """, (like))

    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total

def sale_search(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, invoice_no, customer_id , sale_date,total_amount,discount FROM sales WHERE invoice_no LIKE %s """, (f"%{q}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def reduce_stock(product_id, qty):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE products 
        SET stock_qty = stock_qty - %s 
        WHERE id = %s
    """, (qty, product_id))

    cur.execute("""
    UPDATE products
    SET stock_qty = stock_qty - %s
    WHERE id=%s AND stock_qty >= %s
    """, (qty, product_id, qty))

    if cur.rowcount == 0:
        raise Exception("Insufficient stock!")

    conn.commit()
    cur.close()
    conn.close()
def check_stock(product_id, qty):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT stock_qty 
        FROM products 
        WHERE id=%s
    """, (product_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return False
    
    return row["stock_qty"] >= qty

def cancel_sale(sale_id):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        # ==========================================
        # 1. Validate Sale
        # ==========================================

        cur.execute("""
            SELECT sale_status
            FROM sales
            WHERE id = %s
        """, (sale_id,))

        sale = cur.fetchone()

        if not sale:
            raise ValueError("Sale not found.")

        if sale["sale_status"] == "Cancelled":
            raise ValueError("Sale is already cancelled.")

        # ==========================================
        # 2. Fetch Sale Items
        # ==========================================

        cur.execute("""
            SELECT product_id, qty
            FROM sale_items
            WHERE sale_id = %s
        """, (sale_id,))

        items = cur.fetchall()

        if not items:
            raise ValueError("Sale has no items to cancel.")

        # ==========================================
        # 3. Restore Stock + Create Stock Movement
        # ==========================================

        for item in items:

            # Restore product stock
            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty + %s
                WHERE id = %s
            """, (
                item["qty"],
                item["product_id"]
            ))

            if cur.rowcount == 0:
                raise ValueError(
                    f"Unable to restore stock for "
                    f"Product ID {item['product_id']}."
                )

            # Create stock movement
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
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                item["product_id"],
                item["qty"],
                sale_id
            ))

        # ==========================================
        # 4. Update Sale Status
        # ==========================================

        cur.execute("""
            UPDATE sales
            SET sale_status = 'Cancelled'
            WHERE id = %s
        """, (sale_id,))

        if cur.rowcount == 0:
            raise ValueError(
                f"Unable to cancel Sale ID {sale_id}."
            )

        # ==========================================
        # 5. Commit
        # ==========================================

        conn.commit()

    except Exception:

        # ==========================================
        # Rollback
        # ==========================================

        conn.rollback()
        raise

    finally:

        cur.close()
        conn.close()

def get_sales_summary():

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT

                COUNT(
                    CASE
                        WHEN sale_status = 'Confirmed'
                        THEN 1
                    END
                ) AS total_sales,

                COUNT(
                    CASE
                        WHEN sale_status = 'Confirmed'
                        AND DATE(sale_date) = CURDATE()
                        THEN 1
                    END
                ) AS today_sales,

                COALESCE(
                    SUM(
                        CASE
                            WHEN sale_status = 'Confirmed'
                            THEN total_amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_revenue,

                COUNT(
                    CASE
                        WHEN sale_status = 'Cancelled'
                        THEN 1
                    END
                ) AS cancelled_sales

            FROM sales
        """)

        summary = cur.fetchone()

        return summary

    finally:

        cur.close()
        conn.close()
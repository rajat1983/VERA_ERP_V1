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

        # Validate stock BEFORE inserting
        for item in items:
            if not check_stock(item["product_id"], item["qty"]):
                product = get_product(item["product_id"])
                pname = product["name"] if product else f"Product ID {item['product_id']}"

                raise ValueError(
                    f"Not enough stock for '{pname}'. Requested Qty: {item['qty']}"
                )

        # Insert sale header
        cur.execute("""
            INSERT INTO sales(invoice_no, customer_id, sale_date, remarks, discount, total_amount)
            VALUES (%s,%s,%s,%s,%s,0)
        """, (invoice_no, customer_id, sale_date, remarks, discount))

        sale_id = cur.lastrowid

        # Insert sale items
        for item in items:
            line_total = item["qty"] * item["price"]
            total += line_total

            cur.execute("""
                INSERT INTO sale_items
                (sale_id, product_id, qty, price, line_total)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                sale_id,
                item["product_id"],
                item["qty"],
                item["price"],
                line_total
            ))

            cur.execute("""
                UPDATE products
                SET stock_qty = stock_qty - %s
                WHERE id = %s
            """, (
                item["qty"],
                item["product_id"]
            ))

        discount_percent = float(discount)
        discount_amount = (total * discount_percent) / 100
        total_after_discount = total - discount_amount

        cur.execute("""
            UPDATE sales
            SET total_amount=%s
            WHERE id=%s
        """, (total_after_discount, sale_id))

        conn.commit()
        return sale_id

    except Exception as e:
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

    # 1️⃣ Get old items
    cur.execute("SELECT * FROM sale_items WHERE sale_id=%s", (sale_id,))
    old_items = cur.fetchall()

    # 2️⃣ Return stock for old items
    for item in old_items:
        cur.execute("""
            UPDATE products 
            SET stock_qty = stock_qty + %s 
            WHERE id=%s
        """, (item['qty'], item['product_id']))

    # 3️⃣ Delete old items
    cur.execute("DELETE FROM sale_items WHERE sale_id=%s", (sale_id,))

    # 4️⃣ Update sale header
    cur.execute("""
        UPDATE sales 
        SET customer_id=%s,
            discount=%s,
            total_amount=%s
        WHERE id=%s
    """, (customer_id, discount, total_amount, sale_id))

    # 5️⃣ Insert new items + reduce stock
    for it in items:
        cur.execute("""
            INSERT INTO sale_items 
            (sale_id, product_id, qty, price, line_total)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            sale_id,
            it["product_id"],
            it["qty"],
            it["price"],
            it["line_total"]
        ))

        # reduce stock
        cur.execute("""
            UPDATE products 
            SET stock_qty = stock_qty - %s
            WHERE id=%s
        """, (it["qty"], it["product_id"]))

    conn.commit()
    cur.close()
    conn.close()
    
def cancel_sale(sale_id):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        # ==========================================
        # Validate Sale
        # ==========================================

        cur.execute("""
            SELECT sale_status
            FROM sales
            WHERE id = %s
        """, (sale_id,))

        sale = cur.fetchone()

        if not sale:
            raise Exception("Sale not found.")

        if sale["sale_status"] == "Cancelled":
            raise ValueError("Sale is already cancelled.")

        # ==========================================
        # Fetch Sale Items
        # ==========================================

        cur.execute("""
            SELECT product_id, qty
            FROM sale_items
            WHERE sale_id = %s
        """, (sale_id,))

        items = cur.fetchall()

        # ==========================================
        # Restore Stock
        # ==========================================

        for item in items:

            increase_stock(
                item["product_id"],
                item["qty"]
            )

        # ==========================================
        # Update Sale Status
        # ==========================================

        cur.execute("""
            UPDATE sales
            SET sale_status = 'Cancelled'
            WHERE id = %s
        """, (sale_id,))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()
# def delete_sale(sale_id):
#     conn = get_db_connection()
#     cur = conn.cursor()

#     # 1️⃣ Get items before deleting
#     cur.execute("SELECT product_id, qty FROM sale_items WHERE sale_id=%s", (sale_id,))
#     items = cur.fetchall()

#     # 2️⃣ Restore Stock
#     for item in items:
#         increase_stock(item["product_id"], item["qty"])

#     # 3️⃣ Delete records
#     cur.execute("DELETE FROM sale_items WHERE sale_id=%s", (sale_id,))
#     cur.execute("DELETE FROM sales WHERE id=%s", (sale_id,))

#     conn.commit()
#     cur.close()
#     conn.close()



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

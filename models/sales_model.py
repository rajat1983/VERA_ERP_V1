from db import get_db_connection
from datetime import datetime
from utils.tenant import tid
from utils.totals import calculate_document_totals


def _next_invoice_number(cur):
    year = datetime.now().strftime("%Y")
    lock_name = f"vera_invoice_{year}"
    cur.execute("SELECT GET_LOCK(%s, 10) AS locked", (lock_name,))
    lock = cur.fetchone()
    if not lock or not int(lock["locked"]):
        raise ValueError("Could not allocate invoice number. Please retry.")

    cur.execute(
        """
        SELECT invoice_no
        FROM sales
        WHERE tenant_id=%s AND invoice_no LIKE %s
        ORDER BY invoice_no DESC
        LIMIT 1
        FOR UPDATE
        """,
        (tid(), year + "%"),
    )
    row = cur.fetchone()
    if row and row["invoice_no"]:
        last_seq = int(str(row["invoice_no"])[-5:])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    return f"{year}{next_seq:05d}", lock_name


def get_next_invoice_number():
    conn = get_db_connection()
    cur = conn.cursor()
    lock_name = None
    try:
        invoice, lock_name = _next_invoice_number(cur)
        return invoice
    finally:
        if lock_name:
            cur.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
        cur.close()
        conn.close()


def _sale_user_label():
    return "IFNULL(NULLIF(TRIM(u.full_name), ''), u.username)"


def _sale_filters(search, from_date, to_date, created_by):
    where = [
        "s.tenant_id=%s",
        "(s.invoice_no LIKE %s OR c.name LIKE %s OR IFNULL(u.full_name,'') LIKE %s OR IFNULL(u.username,'') LIKE %s)",
    ]
    like = f"%{search or ''}%"
    params = [tid(), like, like, like, like]
    if from_date:
        where.append("DATE(s.sale_date) >= %s")
        params.append(from_date)
    if to_date:
        where.append("DATE(s.sale_date) <= %s")
        params.append(to_date)
    if created_by:
        where.append("s.created_by = %s")
        params.append(int(created_by))
    return " AND ".join(where), params


def get_all_sales(search, limit, offset, from_date=None, to_date=None, created_by=None):
    conn = get_db_connection()
    cur = conn.cursor()
    where, params = _sale_filters(search, from_date, to_date, created_by)
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT s.id, s.invoice_no, s.sale_status, s.sale_date, s.total_amount, s.discount,
               s.payment_status, c.name AS customer_name,
               s.created_by, {_sale_user_label()} AS generated_by
        FROM sales s
        JOIN customers c ON s.customer_id = c.id
        LEFT JOIN users u ON u.id = s.created_by
        WHERE {where}
        ORDER BY s.id DESC
        LIMIT %s OFFSET %s
        """,
        params,
    )
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def create_sale(customer_id, sale_date, remarks, discount, items, created_by=None):

    conn = get_db_connection()
    cur = conn.cursor()
    lock_name = None

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
        # 1. Validate Stock + attach tax rate
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

            cur.execute(
                "SELECT tax_rate FROM products WHERE id=%s AND tenant_id=%s",
                (item["product_id"], tid()),
            )
            prod = cur.fetchone()
            item["tax_rate"] = float(prod["tax_rate"] if prod else 0)

        totals = calculate_document_totals(items, discount)

        invoice_no, lock_name = _next_invoice_number(cur)

        cur.execute("""
            INSERT INTO sales
            (
                tenant_id,
                invoice_no,
                customer_id,
                sale_date,
                remarks,
                discount,
                discount_amount,
                gst_amount,
                total_amount,
                sale_status,
                payment_status,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Confirmed', 'Pending', %s)
        """, (
            tid(),
            invoice_no,
            customer_id,
            sale_date,
            remarks,
            totals["discount_percent"],
            totals["discount_amount"],
            totals["gst_amount"],
            totals["grand_total"],
            created_by,
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
                    tenant_id,
                    sale_id,
                    product_id,
                    qty,
                    price,
                    line_total
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                tid(),
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
                  AND tenant_id = %s
                  AND stock_qty >= %s
            """, (
                item["qty"],
                item["product_id"],
                tid(),
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
                    tenant_id,
                    product_id,
                    movement_type,
                    quantity,
                    reference_id,
                    reference_type
                )
                VALUES
                (
                    %s,
                    %s,
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                tid(),
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

        if lock_name:
            try:
                cur.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
            except Exception:
                pass
        cur.close()
        conn.close()

def get_product(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM products WHERE id=%s AND tenant_id=%s", (id, tid()))
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
            c.email,
            c.gst_no AS customer_gstin,
            c.city AS customer_city,
            c.state AS customer_state,
            c.pincode AS customer_pincode,
            IFNULL(NULLIF(TRIM(u.full_name), ''), u.username) AS generated_by
        FROM sales s
        JOIN customers c
            ON s.customer_id = c.id
        LEFT JOIN users u ON u.id = s.created_by
        WHERE s.id = %s AND s.tenant_id = %s
    """, (sale_id, tid()))

    sale = cur.fetchone()

    # ============================
    # Sale Items
    # ============================

    cur.execute("""
        SELECT
            si.*,
            p.name AS product_name,
            p.tax_rate,
            p.hsn_code,
            p.unit
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
def update_sale(sale_id, customer_id, discount, items):

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT sale_status FROM sales WHERE id=%s AND tenant_id=%s", (sale_id, tid()))
        existing = cur.fetchone()
        if not existing:
            raise ValueError("Sale not found.")
        if existing["sale_status"] == "Cancelled":
            raise ValueError("Cancelled sale cannot be edited.")

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

        for item in items:
            cur.execute(
                "SELECT tax_rate FROM products WHERE id=%s AND tenant_id=%s",
                (item["product_id"], tid()),
            )
            prod = cur.fetchone()
            item["tax_rate"] = float(prod["tax_rate"] if prod else 0)

        totals = calculate_document_totals(items, discount)

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
                WHERE id = %s AND tenant_id = %s
            """, (
                item["qty"],
                item["product_id"],
                tid(),
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
                    tenant_id,
                    product_id,
                    movement_type,
                    quantity,
                    reference_id,
                    reference_type
                )
                VALUES
                (
                    %s,
                    %s,
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                tid(),
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
                discount_amount = %s,
                gst_amount = %s,
                total_amount = %s
            WHERE id = %s AND tenant_id = %s
        """, (
            customer_id,
            totals["discount_percent"],
            totals["discount_amount"],
            totals["gst_amount"],
            totals["grand_total"],
            sale_id,
            tid(),
        ))

        if cur.rowcount == 0:
            cur.execute("""
                SELECT invoice_no
                FROM sales
                WHERE id = %s AND tenant_id = %s
            """, (sale_id, tid()))

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
                  AND tenant_id = %s
                  AND stock_qty >= %s
            """, (
                item["qty"],
                item["product_id"],
                tid(),
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
                    tenant_id,
                    sale_id,
                    product_id,
                    qty,
                    price,
                    line_total
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                tid(),
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
                    tenant_id,
                    product_id,
                    movement_type,
                    quantity,
                    reference_id,
                    reference_type
                )
                VALUES
                (
                    %s,
                    %s,
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                tid(),
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

def get_sale_count(search, from_date=None, to_date=None, created_by=None):
    conn = get_db_connection()
    cur = conn.cursor()
    where, params = _sale_filters(search, from_date, to_date, created_by)
    cur.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM sales s
        JOIN customers c ON c.id = s.customer_id
        LEFT JOIN users u ON u.id = s.created_by
        WHERE {where}
        """,
        params,
    )
    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total

def sale_search(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, invoice_no, customer_id , sale_date,total_amount,discount FROM sales WHERE tenant_id=%s AND invoice_no LIKE %s """, (tid(), f"%{q}%"))
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
    WHERE id=%s AND tenant_id=%s AND stock_qty >= %s
    """, (qty, product_id, tid(), qty))

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
        WHERE id=%s AND tenant_id=%s
    """, (product_id, tid()))

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
            WHERE id = %s AND tenant_id = %s
        """, (sale_id, tid()))

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
                WHERE id = %s AND tenant_id = %s
            """, (
                item["qty"],
                item["product_id"],
                tid(),
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
                    tenant_id,
                    product_id,
                    movement_type,
                    quantity,
                    reference_id,
                    reference_type
                )
                VALUES
                (
                    %s,
                    %s,
                    'sale',
                    %s,
                    %s,
                    'sale'
                )
            """, (
                tid(),
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
            WHERE id = %s AND tenant_id = %s
        """, (sale_id, tid()))

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

def get_sales_summary(from_date=None, to_date=None, created_by=None, search=""):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        where, params = _sale_filters(search, from_date, to_date, created_by)
        cur.execute(
            f"""
            SELECT
                COUNT(CASE WHEN s.sale_status = 'Confirmed' THEN 1 END) AS total_sales,
                COUNT(CASE WHEN s.sale_status = 'Confirmed' AND DATE(s.sale_date) = CURDATE() THEN 1 END) AS today_sales,
                COALESCE(SUM(CASE WHEN s.sale_status = 'Confirmed' THEN s.total_amount ELSE 0 END), 0) AS total_revenue,
                COUNT(CASE WHEN s.sale_status = 'Cancelled' THEN 1 END) AS cancelled_sales
            FROM sales s
            JOIN customers c ON c.id = s.customer_id
            LEFT JOIN users u ON u.id = s.created_by
            WHERE {where}
            """,
            params,
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()
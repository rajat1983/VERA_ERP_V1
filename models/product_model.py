from db import get_db_connection

# created for Sale entry
def get_products():
    conn = get_db_connection()
    cur = conn.cursor()  
    cur.execute(""" SELECT id,name FROM products  ORDER BY id DESC """)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data
# created for fetch all vendors
def get_vendors():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM vendors ORDER BY name ASC")
    vendors = cur.fetchall()
    cur.close()
    conn.close()
    return vendors

def get_all_products(search, limit, offset):

    conn = get_db_connection()
    cur = conn.cursor()

    like = f"%{search}%"

    cur.execute(""" SELECT 
    p.id,
    p.vendor_id,
    p.name,
    p.image,
    p.sku,
    p.cost_price,
    p.selling_price,
    p.stock_qty,
    p.reorder_level,
    p.status,

    v.name AS vendor_name

FROM products p

LEFT JOIN vendors v
ON p.vendor_id = v.id

WHERE     p.name LIKE %s

    OR p.sku LIKE %s

    OR v.name LIKE %s

ORDER BY p.id DESC

LIMIT %s OFFSET %s

""",

(
    like,
    like,
    like,
    limit,
    offset
))

    data = cur.fetchall()

    cur.close()
    conn.close()

    return data

def get_product_count(search):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM products
        WHERE name LIKE %s OR sku LIKE %s
    """, (like, like))

    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total

def add_product(data):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products
        (
            vendor_id,
            name,
            sku,
            image,
            cost_price,
            selling_price,
            stock_qty,
            reorder_level,
            status
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """, (

        data["vendor_id"],
        data["name"],
        data["sku"],
        data["image"],
        data["cost_price"],
        data["selling_price"],
        data["stock_qty"],
        data["reorder_level"],
        data["status"]

    ))

    conn.commit()
    cur.close()
    conn.close()


def get_product(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row
#Displaying Vendor name on Edit page
def get_product_by_id(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT p.*, v.name AS vendor_name
        FROM products p
        LEFT JOIN vendors v ON p.vendor_id = v.id
        WHERE p.id=%s
    """, (id,))

    row = cur.fetchone()
    cur.close()
    conn.close()
    return row



def update_product(id, data):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE products SET
            vendor_id=%s,
            name=%s,
            sku=%s,
            image=%s,
            cost_price=%s,
            selling_price=%s,
            stock_qty=%s,
            reorder_level=%s,
            status=%s
        WHERE id=%s
    """, (
        data["vendor_id"],
        data["name"],
        data["sku"],
        data["image"],
        data["cost_price"],
        data["selling_price"],
        data["stock_qty"],
        data["reorder_level"],
        data["status"],
        id
    ))
    conn.commit()
    cur.close()
    conn.close()


def delete_product(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()

def product_search(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, cost_price, selling_price,stock_qty ,sku FROM products WHERE name LIKE %s OR sku LIKE %s
    """, (f"%{q}%", f"%{q}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def reduce_stock(product_id, qty):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT stock_qty FROM products WHERE id=%s", (product_id,))
    row = cur.fetchone()

    if not row:
        raise Exception("Product not found")

    current_stock = row["stock_qty"]

    if current_stock < qty:
        raise Exception("Not enough stock available")

    new_stock = current_stock - qty

    cur.execute("UPDATE products SET stock_qty=%s WHERE id=%s",
                (new_stock, product_id))

    conn.commit()
    cur.close()
    conn.close()
    
def increase_stock(product_id, qty):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE products
        SET stock_qty = stock_qty + %s
        WHERE id=%s
    """, (qty, product_id))

    conn.commit()
    cur.close()
    conn.close()
    
def get_products_by_type(product_type):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM products
        WHERE product_type = %s
    """, (product_type,))

    products = cur.fetchall()

    cur.close()
    conn.close()

    return products

def generate_product_code():

    conn = get_db_connection()
    cur = conn.cursor()

    # Get Product Prefix
    cur.execute("""
        SELECT product_prefix
        FROM company
        LIMIT 1
    """)

    company = cur.fetchone()

    prefix = company["product_prefix"] if company else "PRD"

    # Get Last Product ID
    cur.execute("""
        SELECT IFNULL(MAX(id),0) + 1 AS next_id
        FROM products
    """)

    next_id = cur.fetchone()["next_id"]

    product_code = f"{prefix}{next_id:06d}"

    cur.close()
    conn.close()

    return product_code
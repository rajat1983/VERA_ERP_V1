from db import get_db_connection
from utils.tenant import current_tenant_id


def _tid(explicit=None):
    return current_tenant_id()

UNITS = (
    ("pcs", "Pieces"),
    ("pack", "Pack"),
    ("box", "Box"),
    ("kg", "Kg"),
    ("ltr", "Litre"),
    ("dozen", "Dozen"),
    ("set", "Set"),
)


def _blank(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _num(value, default=0):
    if value is None or str(value).strip() == "":
        return default
    return value

# created for Sale entry
def get_products(tenant_id=None):

    conn = get_db_connection()
    cur = conn.cursor()
    tid = _tid(tenant_id)

    cur.execute("""
        SELECT
            id,
            name,
            cost_price,
            selling_price,
            stock_qty,
            tax_rate
        FROM products
        WHERE status='active' AND tenant_id=%s
        ORDER BY name
    """, (tid,))

    products = cur.fetchall()

    cur.close()
    conn.close()

    return products
# created for fetch all vendors
def get_vendors():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, name
    FROM vendors
    WHERE status = 'Active' AND tenant_id=%s
    ORDER BY name ASC
""", (current_tenant_id(),))
    vendors = cur.fetchall()
    cur.close()
    conn.close()
    return vendors

def get_all_products(search, limit, offset, tenant_id=None):

    conn = get_db_connection()
    cur = conn.cursor()
    tid = _tid(tenant_id)

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
ON p.vendor_id = v.id AND v.tenant_id = p.tenant_id

WHERE p.tenant_id=%s
    AND (p.name LIKE %s OR p.sku LIKE %s OR v.name LIKE %s)

ORDER BY p.id DESC

LIMIT %s OFFSET %s

""",

(
    tid,
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

    tid = _tid()
    cur.execute("""
        SELECT COUNT(*) AS total
        FROM products
        WHERE tenant_id=%s AND (name LIKE %s OR sku LIKE %s)
    """, (tid, like, like))

    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total

def add_product(data):

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            INSERT INTO products
            (
                tenant_id,
                vendor_id,
                name,
                short_name,
                brand,
                sku,
                barcode,
                image,
                cost_price,
                selling_price,
                mrp,
                stock_qty,
                reorder_level,
                low_stock_threshold,
                tax_rate,
                hsn_code,
                unit,
                product_type,
                category,
                description,
                notes,
                status
            )
            VALUES
            (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (

            _tid(data.get("tenant_id")),
            _blank(data.get("vendor_id")),
            data["name"],
            _blank(data.get("short_name")),
            _blank(data.get("brand")),
            data["sku"],
            _blank(data.get("barcode")) or data["sku"],
            data["image"],
            data["cost_price"],
            data["selling_price"],
            _num(data.get("mrp"), None),
            data["stock_qty"],
            data["reorder_level"],
            _num(data.get("low_stock_threshold"), 0),
            data.get("tax_rate") or 0,
            _blank(data.get("hsn_code")),
            data.get("unit") or "pcs",
            data.get("product_type") or "finished_goods",
            _blank(data.get("category")),
            _blank(data.get("description")),
            _blank(data.get("notes")),
            data["status"]

        ))
        ensure_category(data.get("category"), _tid(data.get("tenant_id")))

        conn.commit()

        return True

    except Exception as e:

        conn.rollback()

        print("Database Error :", e)

        raise e

    finally:

        cur.close()
        conn.close()


def get_product(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s AND tenant_id=%s", (id, _tid()))
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
        LEFT JOIN vendors v ON p.vendor_id = v.id AND v.tenant_id = p.tenant_id
        WHERE p.id=%s AND p.tenant_id=%s
    """, (id, _tid()))

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
            short_name=%s,
            brand=%s,
            sku=%s,
            barcode=%s,
            image=%s,
            cost_price=%s,
            selling_price=%s,
            mrp=%s,
            reorder_level=%s,
            low_stock_threshold=%s,
            tax_rate=%s,
            hsn_code=%s,
            unit=%s,
            product_type=%s,
            category=%s,
            description=%s,
            notes=%s,
            status=%s
        WHERE id=%s AND tenant_id=%s
    """, (
        _blank(data.get("vendor_id")),
        data["name"],
        _blank(data.get("short_name")),
        _blank(data.get("brand")),
        data["sku"],
        _blank(data.get("barcode")),
        data["image"],
        data["cost_price"],
        data["selling_price"],
        _num(data.get("mrp"), None),
        data["reorder_level"],
        _num(data.get("low_stock_threshold"), 0),
        data.get("tax_rate") or 0,
        _blank(data.get("hsn_code")),
        data.get("unit") or "pcs",
        data.get("product_type") or "finished_goods",
        _blank(data.get("category")),
        _blank(data.get("description")),
        _blank(data.get("notes")),
        data["status"],
        id,
        _tid(data.get("tenant_id")),
    ))
    conn.commit()
    cur.close()
    conn.close()
    ensure_category(data.get("category"), _tid(data.get("tenant_id")))
    return True


def delete_product(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s AND tenant_id=%s", (id, _tid()))
    conn.commit()
    cur.close()
    conn.close()

def product_search(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, cost_price, selling_price,stock_qty ,sku FROM products
        WHERE tenant_id=%s AND (name LIKE %s OR sku LIKE %s)
    """, (_tid(), f"%{q}%", f"%{q}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def reduce_stock(product_id, qty):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT stock_qty FROM products WHERE id=%s AND tenant_id=%s", (product_id, _tid()))
    row = cur.fetchone()

    if not row:
        raise Exception("Product not found")

    current_stock = row["stock_qty"]

    if current_stock < qty:
        raise Exception("Not enough stock available")

    new_stock = current_stock - qty

    cur.execute("UPDATE products SET stock_qty=%s WHERE id=%s AND tenant_id=%s",
                (new_stock, product_id, _tid()))

    conn.commit()
    cur.close()
    conn.close()
    
def increase_stock(product_id, qty):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE products
        SET stock_qty = stock_qty + %s
        WHERE id=%s AND tenant_id=%s
    """, (qty, product_id, _tid()))

    conn.commit()
    cur.close()
    conn.close()
    
def get_products_by_type(product_type):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM products
        WHERE product_type = %s AND tenant_id=%s
    """, (product_type, _tid()))

    products = cur.fetchall()

    cur.close()
    conn.close()

    return products

def generate_product_code():

    conn = get_db_connection()
    cur = conn.cursor()

    # Get Product Prefix
    tid = _tid()
    cur.execute("""
        SELECT product_prefix
        FROM company
        WHERE tenant_id=%s
        LIMIT 1
    """, (tid,))

    company = cur.fetchone()

    prefix = company["product_prefix"] if company else "PRD"

    # Get Last Product ID
    cur.execute("""
        SELECT IFNULL(MAX(id),0) + 1 AS next_id
        FROM products
        WHERE tenant_id=%s
    """, (tid,))

    next_id = cur.fetchone()["next_id"]

    product_code = f"{prefix}{next_id:06d}"

    cur.close()
    conn.close()

    return product_code
def product_name_exists(name, exclude_id=None):

    conn = get_db_connection()
    cur = conn.cursor()

    if exclude_id:

        cur.execute("""
            SELECT id
            FROM products
            WHERE tenant_id=%s
            AND LOWER(name)=LOWER(%s)
            AND id<>%s
        """, (_tid(), name, exclude_id))

    else:

        cur.execute("""
            SELECT id
            FROM products
            WHERE tenant_id=%s
            AND LOWER(name)=LOWER(%s)
        """, (_tid(), name,))

    product = cur.fetchone()

    cur.close()
    conn.close()

    return product is not None


def search_categories(q=""):
    conn = get_db_connection()
    cur = conn.cursor()
    q = (q or "").strip()
    if q:
        cur.execute(
            """
            SELECT id, name FROM product_categories
            WHERE tenant_id=%s AND name LIKE %s
            ORDER BY name
            LIMIT 20
            """,
            (_tid(), f"%{q}%"),
        )
    else:
        cur.execute(
            """
            SELECT id, name FROM product_categories
            WHERE tenant_id=%s
            ORDER BY name
            LIMIT 50
            """,
            (_tid(),),
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def category_exists(name, exclude_id=None, tenant_id=None):
    conn = get_db_connection()
    cur = conn.cursor()
    tid = _tid(tenant_id)
    if exclude_id:
        cur.execute(
            "SELECT id FROM product_categories WHERE tenant_id=%s AND LOWER(name)=LOWER(%s) AND id<>%s LIMIT 1",
            (tid, name, exclude_id),
        )
    else:
        cur.execute(
            "SELECT id FROM product_categories WHERE tenant_id=%s AND LOWER(name)=LOWER(%s) LIMIT 1",
            (tid, name),
        )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return bool(row)


def add_category(name, tenant_id=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("Category name is required.")
    tid = _tid(tenant_id)
    if category_exists(name, tenant_id=tid):
        raise ValueError("This category already exists.")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO product_categories (tenant_id, name) VALUES (%s, %s)", (tid, name))
    conn.commit()
    category_id = cur.lastrowid
    cur.close()
    conn.close()
    return {"id": category_id, "name": name}


def ensure_category(name, tenant_id=None):
    name = (name or "").strip()
    if not name:
        return None
    tid = _tid(tenant_id)
    if category_exists(name, tenant_id=tid):
        return name
    add_category(name, tenant_id=tid)
    return name


def can_delete_product(id):
    row = get_product_by_id(id)
    if not row:
        return False, "Product not found."
    conn = get_db_connection()
    cur = conn.cursor()
    tenant_id = _tid()
    checks = (
        ("SELECT COUNT(*) AS c FROM sale_items WHERE tenant_id=%s AND product_id=%s", "sales invoices"),
        ("SELECT COUNT(*) AS c FROM purchase_items WHERE tenant_id=%s AND product_id=%s", "purchase orders"),
        ("SELECT COUNT(*) AS c FROM pos_sale_items WHERE tenant_id=%s AND product_id=%s", "POS bills"),
        ("SELECT COUNT(*) AS c FROM production_batches WHERE tenant_id=%s AND product_id=%s", "production batches"),
        ("SELECT COUNT(*) AS c FROM production_materials WHERE tenant_id=%s AND raw_material_id=%s", "production recipes"),
    )
    try:
        for sql, label in checks:
            cur.execute(sql, (tenant_id, id))
            if cur.fetchone()["c"]:
                return False, f"Cannot delete: this product is used on {label}."
    finally:
        cur.close()
        conn.close()
    return True, ""
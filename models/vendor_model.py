from db import get_db_connection
from utils.tenant import tid

def get_all_vendors(search, limit, offset):

    conn = get_db_connection()
    cur = conn.cursor()

    like = f"%{search}%"

    cur.execute("""

        SELECT *

        FROM vendors

        WHERE tenant_id=%s AND (

            vendor_code LIKE %s

            OR name LIKE %s

            OR phone LIKE %s

            OR email LIKE %s

            OR gst_number LIKE %s

            OR city LIKE %s

        )

        ORDER BY id DESC

        LIMIT %s OFFSET %s

    """, (

        tid(),
        like,
        like,
        like,
        like,
        like,
        like,

        limit,
        offset

    ))

    vendors = cur.fetchall()

    cur.close()
    conn.close()

    return vendors

def get_vendor_count(search):

    conn = get_db_connection()
    cur = conn.cursor()

    like = f"%{search}%"

    cur.execute("""

        SELECT COUNT(*) AS total

        FROM vendors

        WHERE tenant_id=%s AND (

            vendor_code LIKE %s

            OR name LIKE %s

            OR phone LIKE %s

            OR email LIKE %s

            OR gst_number LIKE %s

            OR city LIKE %s

        )

    """, (

        tid(),
        like,
        like,
        like,
        like,
        like,
        like

    ))

    total = cur.fetchone()["total"]

    cur.close()
    conn.close()

    return total

def vendor_search(q):

    conn = get_db_connection()
    cur = conn.cursor()

    like = f"%{q}%"

    cur.execute("""

        SELECT

            id,
            vendor_code,
            name,
            email,
            phone,
            address,
            city,
            gst_number,
            status

        FROM vendors

        WHERE tenant_id=%s AND (

            vendor_code LIKE %s

            OR name LIKE %s

            OR phone LIKE %s

            OR email LIKE %s

            OR gst_number LIKE %s

            OR city LIKE %s

        )

        ORDER BY id DESC

    """, (

        tid(),
        like,
        like,
        like,
        like,
        like,
        like

    ))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def get_vendor(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM vendors WHERE id=%s AND tenant_id=%s", (id, tid()))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def add_vendor(
    vendor_code,
    name,
    email,
    phone,
    gst_number,
    address,
    city,
    state,
    pincode,
    status
):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""

        INSERT INTO vendors
        (

            tenant_id,
            vendor_code,
            name,
            email,
            phone,
            gst_number,
            address,
            city,
            state,
            pincode,
            status

        )

        VALUES
        (

            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s

        )

    """, (

        tid(),
        vendor_code,
        name,
        email,
        phone,
        gst_number,
        address,
        city,
        state,
        pincode,
        status

    ))

    conn.commit()

    cur.close()
    conn.close()


# ==========================================
# Update Vendor
# ==========================================

def update_vendor(
    id,
    name,
    email,
    phone,
    gst_number,
    address,
    city,
    state,
    pincode,
    status
):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""

        UPDATE vendors

        SET

            name = %s,
            email = %s,
            phone = %s,
            gst_number = %s,
            address = %s,
            city = %s,
            state = %s,
            pincode = %s,
            status = %s,
            updated_at = NOW()

        WHERE id = %s AND tenant_id = %s

    """, (

        name,
        email,
        phone,
        gst_number,
        address,
        city,
        state,
        pincode,
        status,
        id,
        tid(),

    ))

    conn.commit()

    cur.close()
    conn.close()


def can_delete_vendor(id):
    row = get_vendor_by_id(id)
    if not row:
        return False, "Vendor not found."
    conn = get_db_connection()
    cur = conn.cursor()
    tenant_id = tid()
    try:
        cur.execute(
            "SELECT COUNT(*) AS c FROM purchases WHERE tenant_id=%s AND vendor_id=%s",
            (tenant_id, id),
        )
        if cur.fetchone()["c"]:
            return False, "Cannot delete: this vendor has purchase orders."
        cur.execute(
            "SELECT COUNT(*) AS c FROM products WHERE tenant_id=%s AND vendor_id=%s",
            (tenant_id, id),
        )
        if cur.fetchone()["c"]:
            return False, "Cannot delete: products are linked to this vendor."
    finally:
        cur.close()
        conn.close()
    return True, ""


def delete_vendor(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM vendors WHERE id=%s AND tenant_id=%s", (id, tid()))
    conn.commit()
    cur.close()
    conn.close()
    
def search_vendors(q):
    conn = get_db_connection()
    cur = conn.cursor()

    like = f"%{q.lower()}%"

    cur.execute("""
        SELECT
            id,
            vendor_code,
            name
        FROM vendors
        WHERE tenant_id=%s AND (
            LOWER(name) LIKE %s
            OR LOWER(vendor_code) LIKE %s
        )
        ORDER BY name
        LIMIT 10
    """, (tid(), like, like))

    vendors = cur.fetchall()

    cur.close()
    conn.close()

    return vendors
def create_vendor(name, phone="", email="", address=""):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO vendors (tenant_id, name, phone, email, address)
        VALUES (%s, %s, %s, %s, %s)
    """, (tid(), name, phone, email, address))
    conn.commit()
    vendor_id = cur.lastrowid
    cur.close()
    conn.close()
    return vendor_id

def get_vendor_email(vendor_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT email FROM vendors WHERE id=%s AND tenant_id=%s", (vendor_id, tid()))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row["email"] if row and row["email"] else None
# ==========================================
# Generate Vendor Code
# ==========================================

def generate_vendor_code():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""

        SELECT MAX(id) AS max_id

        FROM vendors
        WHERE tenant_id=%s

    """, (tid(),))

    row = cur.fetchone()

    next_id = 1

    if row and row["max_id"]:

        next_id = row["max_id"] + 1

    vendor_code = f"VEN{next_id:06d}"

    cur.close()
    conn.close()

    return vendor_code

def get_vendor_by_id(id):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""

        SELECT *

        FROM vendors

        WHERE id=%s AND tenant_id=%s

    """, (id, tid()))

    vendor = cur.fetchone()

    cur.close()
    conn.close()

    return vendor
# ==========================================
# Check Duplicate Vendor
# ==========================================

def check_duplicate_vendor(
    email,
    phone,
    gst_number,
    exclude_id=None
):

    conn = get_db_connection()
    cur = conn.cursor()
    tenant_id = tid()

    def exists(column, value):
        if not value:
            return False
        sql = f"SELECT id FROM vendors WHERE tenant_id=%s AND {column}=%s"
        params = [tenant_id, value]
        if exclude_id:
            sql += " AND id<>%s"
            params.append(exclude_id)
        sql += " LIMIT 1"
        cur.execute(sql, params)
        return cur.fetchone() is not None

    email_exists = exists("email", email)
    phone_exists = exists("phone", phone)
    gst_exists = exists("gst_number", gst_number) if gst_number else False

    cur.close()
    conn.close()

    return (

        email_exists,
        phone_exists,
        gst_exists

    )
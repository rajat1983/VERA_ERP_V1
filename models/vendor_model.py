from db import get_db_connection

def get_all_vendors(search, limit, offset):

    conn = get_db_connection()
    cur = conn.cursor()

    like = f"%{search}%"

    cur.execute("""

        SELECT *

        FROM vendors

        WHERE

            vendor_code LIKE %s

            OR name LIKE %s

            OR phone LIKE %s

            OR email LIKE %s

            OR gst_number LIKE %s

            OR city LIKE %s

        ORDER BY id DESC

        LIMIT %s OFFSET %s

    """, (

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

        WHERE

            vendor_code LIKE %s

            OR name LIKE %s

            OR phone LIKE %s

            OR email LIKE %s

            OR gst_number LIKE %s

            OR city LIKE %s

    """, (

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

        WHERE

            vendor_code LIKE %s

            OR name LIKE %s

            OR phone LIKE %s

            OR email LIKE %s

            OR gst_number LIKE %s

            OR city LIKE %s

        ORDER BY id DESC

    """, (

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
    cur.execute("SELECT * FROM vendors WHERE id=%s", (id,))
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

            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s

        )

    """, (

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

        WHERE id = %s

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
        id

    ))

    conn.commit()

    cur.close()
    conn.close()


def delete_vendor(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM vendors WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    
def search_vendors(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name 
        FROM vendors 
        WHERE LOWER(name) LIKE %s 
        ORDER BY name 
        LIMIT 10
    """, (f"%{q.lower()}%",))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
def create_vendor(name, phone="", email="", address=""):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO vendors (name, phone, email, address)
        VALUES (%s, %s, %s, %s)
    """, (name, phone, email, address))
    conn.commit()
    vendor_id = cur.lastrowid
    cur.close()
    conn.close()
    return vendor_id

def get_vendor_email(vendor_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT email FROM vendors WHERE id=%s", (vendor_id,))
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

    """)

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

        WHERE id=%s

    """, (id,))

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

    # -----------------------------
    # Check Email
    # -----------------------------

    if exclude_id:

        cur.execute("""

            SELECT id

            FROM vendors

            WHERE email=%s
              AND id<>%s
            LIMIT 1

        """, (

            email,
            exclude_id

        ))

    else:

        cur.execute("""

            SELECT id

            FROM vendors

            WHERE email=%s
            LIMIT 1

        """, (

            email,

        ))

    email_exists = cur.fetchone() is not None

    # -----------------------------
    # Check Mobile
    # -----------------------------

    if exclude_id:

        cur.execute("""

            SELECT id

            FROM vendors

            WHERE phone=%s
              AND id<>%s
            LIMIT 1

        """, (

            phone,
            exclude_id

        ))

    else:

        cur.execute("""

            SELECT id

            FROM vendors

            WHERE phone=%s
            LIMIT 1

        """, (

            phone,

        ))

    phone_exists = cur.fetchone() is not None

    # -----------------------------
    # Check GST
    # -----------------------------

    gst_exists = False

    if gst_number:

        if exclude_id:

            cur.execute("""

                SELECT id

                FROM vendors

                WHERE gst_number=%s
                  AND id<>%s
                LIMIT 1

            """, (

                gst_number,
                exclude_id

            ))

        else:

            cur.execute("""

                SELECT id

                FROM vendors

                WHERE gst_number=%s
                LIMIT 1

            """, (

                gst_number,

            ))

        gst_exists = cur.fetchone() is not None

    cur.close()
    conn.close()

    return (

        email_exists,
        phone_exists,
        gst_exists

    )
from db import get_db_connection
# created for Sale entry
def get_customers():
    conn = get_db_connection()
    cur = conn.cursor()  
    cur.execute("""
        SELECT id, name FROM customers
        WHERE LOWER(IFNULL(status, 'active')) = 'active'
        ORDER BY name
    """)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_all_customers(search, limit, offset):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
    SELECT
        id,
        customer_code,
        name,
        phone,
        email,
        city,
        status,
        created_at
    FROM customers
    WHERE name LIKE %s
       OR email LIKE %s
       OR phone LIKE %s
       OR customer_code LIKE %s
    ORDER BY id DESC
    LIMIT %s OFFSET %s
""", (
    like,
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



def get_customer_count(search):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM customers WHERE name LIKE %s OR email LIKE %s
    """, (like, like))

    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total
    
# ==========================================
# Generate Customer Code
# ==========================================

def generate_customer_code():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT customer_code
        FROM customers
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row and row["customer_code"]:

        last_no = int(row["customer_code"].replace("CUS", ""))

        return f"CUS{last_no + 1:06d}"

    return "CUS000001"
# ==========================================
# Check Duplicate Customer
# ==========================================

# ==========================================
# Check Duplicate Customer
# ==========================================

def _digits_only(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())


def check_duplicate_customer(
    email,
    phone,
    exclude_id=None
):

    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT email, phone FROM customers"
    params = []

    if exclude_id is not None:
        query += " WHERE id<>%s"
        params.append(exclude_id)

    cur.execute(query, tuple(params))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    email_norm = (email or "").strip().lower()
    phone_digits = _digits_only(phone)

    email_exists = False
    phone_exists = False

    for row in rows:
        row_email = (row.get("email") or "").strip().lower()
        if email_norm and row_email and row_email == email_norm:
            email_exists = True
        if phone_digits and _digits_only(row.get("phone")) == phone_digits:
            phone_exists = True

    return email_exists, phone_exists

def _empty_to_none(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def add_customer(customer_code, name, email, phone, gst_no, address, city,state, pincode,  status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""

INSERT INTO customers
(customer_code,name,email,phone,gst_no,address,city,state,pincode,status)

VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

""", (
        customer_code,
        name,
        _empty_to_none(email),
        _empty_to_none(phone),
        _empty_to_none(gst_no),
        _empty_to_none(address),
        _empty_to_none(city),
        _empty_to_none(state),
        _empty_to_none(pincode),
        status or "Active",
    ))
    conn.commit()
    customer_id = cur.lastrowid
    cur.close()
    conn.close()
    return customer_id


def get_customer_by_id(cid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=%s", (cid,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    return data


# ==========================================
# Update Customer
# ==========================================

def update_customer(
    cid,
    name,
    email,
    phone,
    gst_no,
    address,
    city,
    state,
    pincode,
    status
):

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE customers
        SET
            name = %s,
            email = %s,
            phone = %s,
            gst_no = %s,
            address = %s,
            city = %s,
            state = %s,
            pincode = %s,
            status = %s
        WHERE id = %s
    """, (
        name,
        email,
        phone,
        gst_no,
        address,
        city,
        state,
        pincode,
        status,
        cid
    ))

    conn.commit()

    cur.close()
    conn.close()


def delete_customer(cid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
    conn.commit()
    cur.close()
    conn.close()


def search_customers(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM customers
        WHERE name LIKE %s OR email LIKE %s OR phone LIKE %s
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def search_customers_for_sale(q, limit=12):
    q = (q or "").strip()
    if not q:
        return []
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{q}%"
    cur.execute(
        """
        SELECT id, name, phone
        FROM customers
        WHERE LOWER(IFNULL(status, 'active')) = 'active'
          AND (name LIKE %s OR phone LIKE %s OR IFNULL(customer_code, '') LIKE %s)
        ORDER BY name
        LIMIT %s
        """,
        (like, like, like, int(limit)),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

from db import get_db_connection

def get_all_vendors(search, limit, offset):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT * FROM vendors
        WHERE name LIKE %s OR email LIKE %s 
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """, (like, like, limit, offset))

    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_vendor_count(search):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM vendors
        WHERE name LIKE %s OR email LIKE %s
    """, (like, like))

    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total

def vendor_search(q):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, email, phone,address,gst_number,status FROM vendors WHERE name LIKE %s OR email LIKE %s
    """, (f"%{q}%", f"%{q}%"))
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


def add_vendor(name, email, phone, address,gst,sts):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO vendors (name,email,phone,address,gst_number,status) VALUES (%s,%s,%s,%s,%s,%s)",
        (name, email, phone, address,gst,sts)
    )
    conn.commit()
    cur.close()
    conn.close()


def update_vendor(id, name, email, phone, address,gst,sts):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE vendors SET name=%s,email=%s,phone=%s,address=%s,gst_number=%s,status=%s WHERE id=%s",
        (name, email, phone, address,gst,sts, id)
    )
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



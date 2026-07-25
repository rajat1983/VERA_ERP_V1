from db import get_db_connection
# created for Sale entry
def get_customers():
    conn = get_db_connection()
    cur = conn.cursor()  
    cur.execute(""" SELECT id,name FROM customers  ORDER BY id DESC """)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_all_customers(search, limit, offset):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search}%"

    cur.execute("""
        SELECT * FROM customers
        WHERE name LIKE %s OR email LIKE %s
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """, (like, like, limit, offset))
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
    

def add_customer(name, email, phone, address, status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO customers (name, email, phone, address, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, email, phone,address,status))
    conn.commit()
    cur.close()
    conn.close()


def get_customer_by_id(cid):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id=%s", (cid,))
    data = cur.fetchone()
    cur.close()
    conn.close()
    return data


def update_customer(cid, name, email, phone, address, status):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE customers
        SET name=%s, email=%s, phone=%s, address=%s, status=%s
        WHERE id=%s
    """, (name, email, phone, address, status, cid))
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

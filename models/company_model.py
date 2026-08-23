from db import get_db_connection


def get_company():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM company
        LIMIT 1
    """)

    company = cur.fetchone()

    cur.close()
    conn.close()

    return company


def save_company(data):
    fields = [
        "company_name",
        "address1",
        "address2",
        "city",
        "state",
        "pincode",
        "gstin",
        "phone",
        "email",
        "product_prefix",
    ]
    values = {k: (data.get(k) or "").strip() for k in fields}
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM company LIMIT 1")
    row = cur.fetchone()
    if row:
        sets = ", ".join(f"{k}=%s" for k in fields)
        cur.execute(
            f"UPDATE company SET {sets} WHERE id=%s",
            [values[k] for k in fields] + [row["id"]],
        )
    else:
        cols = ", ".join(fields)
        placeholders = ", ".join(["%s"] * len(fields))
        cur.execute(
            f"INSERT INTO company ({cols}) VALUES ({placeholders})",
            [values[k] for k in fields],
        )
    conn.commit()
    cur.close()
    conn.close()
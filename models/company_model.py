from db import get_db_connection
from utils.tenant import tid


def get_company():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM company WHERE tenant_id=%s LIMIT 1", (tid(),))
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
    tenant_id = tid()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM company WHERE tenant_id=%s LIMIT 1", (tenant_id,))
    row = cur.fetchone()
    if row:
        sets = ", ".join(f"{k}=%s" for k in fields)
        cur.execute(
            f"UPDATE company SET {sets} WHERE id=%s AND tenant_id=%s",
            [values[k] for k in fields] + [row["id"], tenant_id],
        )
    else:
        cols = ", ".join(["tenant_id"] + fields)
        placeholders = ", ".join(["%s"] * (len(fields) + 1))
        cur.execute(
            f"INSERT INTO company ({cols}) VALUES ({placeholders})",
            [tenant_id] + [values[k] for k in fields],
        )
    conn.commit()
    cur.close()
    conn.close()

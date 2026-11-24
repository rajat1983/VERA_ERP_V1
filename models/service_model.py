from db import get_db_connection


UNITS = ("page", "piece", "set")


def list_services(search="", limit=10, offset=0):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search or ''}%"
    cur.execute(
        """
        SELECT id, name, category, unit, price, is_active, created_at
        FROM services
        WHERE name LIKE %s OR IFNULL(category, '') LIKE %s OR unit LIKE %s
        ORDER BY name
        LIMIT %s OFFSET %s
        """,
        (like, like, like, int(limit), int(offset)),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def count_services(search=""):
    conn = get_db_connection()
    cur = conn.cursor()
    like = f"%{search or ''}%"
    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM services
        WHERE name LIKE %s OR IFNULL(category, '') LIKE %s OR unit LIKE %s
        """,
        (like, like, like),
    )
    total = cur.fetchone()["total"]
    cur.close()
    conn.close()
    return total


def get_service(service_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM services WHERE id=%s", (service_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def name_exists(name, exclude_id=None):
    conn = get_db_connection()
    cur = conn.cursor()
    if exclude_id:
        cur.execute(
            "SELECT id FROM services WHERE LOWER(name)=LOWER(%s) AND id<>%s LIMIT 1",
            (name, exclude_id),
        )
    else:
        cur.execute("SELECT id FROM services WHERE LOWER(name)=LOWER(%s) LIMIT 1", (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return bool(row)


def add_service(name, category, unit, price, is_active):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO services (name, category, unit, price, is_active)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (name, category or None, unit, price, 1 if is_active else 0),
    )
    conn.commit()
    service_id = cur.lastrowid
    cur.close()
    conn.close()
    ensure_category(category)
    return service_id


def update_service(service_id, name, category, unit, price, is_active):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE services
        SET name=%s, category=%s, unit=%s, price=%s, is_active=%s
        WHERE id=%s
        """,
        (name, category or None, unit, price, 1 if is_active else 0, service_id),
    )
    conn.commit()
    cur.close()
    conn.close()
    ensure_category(category)


def delete_service(service_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM services WHERE id=%s", (service_id,))
    conn.commit()
    cur.close()
    conn.close()


def search_categories(q=""):
    conn = get_db_connection()
    cur = conn.cursor()
    q = (q or "").strip()
    if q:
        cur.execute(
            """
            SELECT id, name FROM service_categories
            WHERE name LIKE %s
            ORDER BY name
            LIMIT 20
            """,
            (f"%{q}%",),
        )
    else:
        cur.execute(
            """
            SELECT id, name FROM service_categories
            ORDER BY name
            LIMIT 50
            """
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def category_exists(name, exclude_id=None):
    conn = get_db_connection()
    cur = conn.cursor()
    if exclude_id:
        cur.execute(
            "SELECT id FROM service_categories WHERE LOWER(name)=LOWER(%s) AND id<>%s LIMIT 1",
            (name, exclude_id),
        )
    else:
        cur.execute(
            "SELECT id FROM service_categories WHERE LOWER(name)=LOWER(%s) LIMIT 1",
            (name,),
        )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return bool(row)


def add_category(name):
    name = (name or "").strip()
    if not name:
        raise ValueError("Category name is required.")
    if category_exists(name):
        raise ValueError("This category already exists.")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO service_categories (name) VALUES (%s)", (name,))
    conn.commit()
    category_id = cur.lastrowid
    cur.close()
    conn.close()
    return {"id": category_id, "name": name}


def ensure_category(name):
    name = (name or "").strip()
    if not name:
        return None
    if category_exists(name):
        return name
    add_category(name)
    return name


def active_catalog(search="", category=""):
    conn = get_db_connection()
    cur = conn.cursor()
    where = ["is_active=1"]
    params = []
    if category:
        where.append("category=%s")
        params.append(category)
    if search:
        where.append("(name LIKE %s OR IFNULL(category,'') LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like])
    cur.execute(
        f"""
        SELECT id, name, category, unit, price
        FROM services
        WHERE {" AND ".join(where)}
        ORDER BY name
        LIMIT 200
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

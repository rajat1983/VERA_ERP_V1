from db import get_db_connection


def _has_table(cur, table):
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table,),
    )
    return cur.fetchone()["c"] > 0


def _has_column(cur, table, column):
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cur.fetchone()["c"] > 0


def get_by_shop_code(shop_code):
    code = (shop_code or "").strip().upper()
    if not code:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, shop_code, name, slug, status
            FROM tenants
            WHERE shop_code=%s
            LIMIT 1
            """,
            (code,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def get_by_id(tenant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, shop_code, name, slug, status
            FROM tenants
            WHERE id=%s
            LIMIT 1
            """,
            (tenant_id,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def next_shop_code():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT GET_LOCK('vera_shop_code', 10) AS locked")
        locked = cur.fetchone()
        if not locked or not locked["locked"]:
            raise RuntimeError("Could not allocate a shop code.")
        cur.execute(
            """
            SELECT IFNULL(MAX(CAST(SUBSTRING(shop_code, 5) AS UNSIGNED)), 0) + 1 AS next_n
            FROM tenants
            WHERE shop_code LIKE 'SHOP%%'
            """
        )
        next_n = int(cur.fetchone()["next_n"] or 1)
        return f"SHOP{next_n:04d}"
    finally:
        try:
            cur.execute("SELECT RELEASE_LOCK('vera_shop_code')")
        except Exception:
            pass
        cur.close()
        conn.close()


def list_tenants(status=None, search=""):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        where = ["1=1"]
        params = []
        if status:
            where.append("t.status=%s")
            params.append(status)
        if search:
            where.append("(t.name LIKE %s OR t.shop_code LIKE %s)")
            like = f"%{search.strip()}%"
            params.extend([like, like])
        cur.execute(
            f"""
            SELECT t.id, t.shop_code, t.name, t.slug, t.status, t.created_at,
                   (SELECT COUNT(*) FROM users u WHERE u.tenant_id=t.id) AS user_count
            FROM tenants t
            WHERE {" AND ".join(where)}
            ORDER BY t.id DESC
            """,
            params,
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def counts():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(status='active') AS active,
              SUM(status='suspended') AS suspended
            FROM tenants
            """
        )
        row = cur.fetchone() or {}
        return {
            "total": int(row.get("total") or 0),
            "active": int(row.get("active") or 0),
            "suspended": int(row.get("suspended") or 0),
        }
    finally:
        cur.close()
        conn.close()


def set_status(tenant_id, status):
    status = (status or "").strip().lower()
    if status not in ("active", "suspended"):
        raise ValueError("Status must be active or suspended.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE tenants SET status=%s WHERE id=%s", (status, tenant_id))
        if cur.rowcount == 0:
            raise ValueError("Shop not found.")
        conn.commit()
    except ValueError:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def list_shop_users(tenant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT u.id, u.username, u.full_name, u.email, u.status, u.is_active, r.name AS role
            FROM users u
            LEFT JOIN roles r ON r.id = u.role_id
            WHERE u.tenant_id=%s
            ORDER BY u.id
            """,
            (tenant_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def delete_tenant(tenant_id):
    """Remove a shop that has not taken operational data. Used if onboarding fails."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if _has_table(cur, "users"):
            cur.execute("DELETE FROM users WHERE tenant_id=%s", (tenant_id,))
        if _has_table(cur, "company") and _has_column(cur, "company", "tenant_id"):
            cur.execute("DELETE FROM company WHERE tenant_id=%s", (tenant_id,))
        cur.execute("DELETE FROM tenants WHERE id=%s", (tenant_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def create_tenant(name, shop_code=None, status="active"):
    name = (name or "").strip() or "Shop"
    code = (shop_code or next_shop_code()).strip().upper()
    slug = code.lower()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO tenants (shop_code, name, slug, status)
            VALUES (%s, %s, %s, %s)
            """,
            (code, name, slug, status),
        )
        tenant_id = cur.lastrowid
        try:
            if _has_table(cur, "company") and _has_column(cur, "company", "tenant_id"):
                cur.execute(
                    """
                    INSERT INTO company (tenant_id, company_name, product_prefix)
                    VALUES (%s, %s, 'PRD')
                    """,
                    (tenant_id, name),
                )
        except Exception:
            pass
        conn.commit()
        return {"id": tenant_id, "shop_code": code, "name": name, "slug": slug, "status": status}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

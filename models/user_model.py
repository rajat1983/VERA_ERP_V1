from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection


def _role_id(cur, name):
    cur.execute("SELECT id FROM roles WHERE name=%s", (name,))
    row = cur.fetchone()
    return row["id"] if row else None


def ensure_default_admin():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        seeds = (
            ("admin", "admin123", "admin"),
            ("manager", "manager123", "manager"),
            ("staff", "staff123", "staff"),
        )
        for username, password, role_name in seeds:
            cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cur.fetchone():
                continue
            rid = _role_id(cur, role_name)
            if not rid:
                continue
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role_id, is_active)
                VALUES (%s, %s, %s, 1)
                """,
                (username, generate_password_hash(password), rid),
            )
            if _has_role_col(cur):
                cur.execute("UPDATE users SET role=%s WHERE username=%s", (role_name, username))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def _has_role_col(cur):
    cur.execute(
        """
        SELECT COUNT(*) AS c FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='users' AND COLUMN_NAME='role'
        """
    )
    return cur.fetchone()["c"] > 0


def authenticate(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT u.id, u.username, u.password_hash, u.is_active, u.role_id,
                   r.name AS role
            FROM users u
            LEFT JOIN roles r ON r.id = u.role_id
            WHERE u.username=%s
            """,
            (username,),
        )
        user = cur.fetchone()
        if not user:
            return None
        if user.get("is_active") in (0, "0", False):
            return None
        if check_password_hash(user["password_hash"], password):
            user["role"] = (user.get("role") or "staff").lower()
            return user
        return None
    finally:
        cur.close()
        conn.close()


def list_users():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.id, u.username, u.is_active, u.role_id, r.name AS role, r.description AS role_description
        FROM users u
        LEFT JOIN roles r ON r.id = u.role_id
        ORDER BY u.id
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def list_roles():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description FROM roles ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.id, u.username, u.is_active, u.role_id, r.name AS role
        FROM users u
        LEFT JOIN roles r ON r.id = u.role_id
        WHERE u.id=%s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def count_active_admins(exclude_id=None):
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
        SELECT COUNT(*) AS c
        FROM users u
        JOIN roles r ON r.id = u.role_id
        WHERE r.name='admin' AND u.is_active=1
    """
    params = []
    if exclude_id:
        sql += " AND u.id <> %s"
        params.append(exclude_id)
    cur.execute(sql, params)
    total = cur.fetchone()["c"]
    cur.close()
    conn.close()
    return int(total)


def create_user(username, password, role_id, is_active=1):
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("Username and password are required.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            raise ValueError("Username already exists.")
        cur.execute("SELECT name FROM roles WHERE id=%s", (role_id,))
        role = cur.fetchone()
        if not role:
            raise ValueError("Invalid role.")
        cur.execute(
            "INSERT INTO users (username, password_hash, role_id, is_active) VALUES (%s, %s, %s, %s)",
            (username, generate_password_hash(password), role_id, 1 if is_active else 0),
        )
        if _has_role_col(cur):
            cur.execute("UPDATE users SET role=%s WHERE username=%s", (role["name"], username))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_user(user_id, role_id, is_active, password=None):
    existing = get_user(user_id)
    if not existing:
        raise ValueError("User not found.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM roles WHERE id=%s", (role_id,))
        role = cur.fetchone()
        if not role:
            raise ValueError("Invalid role.")
        becoming_non_admin = role["name"] != "admin" or not is_active
        if existing.get("role") == "admin" and becoming_non_admin:
            if count_active_admins(exclude_id=user_id) < 1:
                raise ValueError("Keep at least one active admin.")
        cur.execute(
            "UPDATE users SET role_id=%s, is_active=%s WHERE id=%s",
            (role_id, 1 if is_active else 0, user_id),
        )
        if _has_role_col(cur):
            cur.execute("UPDATE users SET role=%s WHERE id=%s", (role["name"], user_id))
        if password:
            cur.execute(
                "UPDATE users SET password_hash=%s WHERE id=%s",
                (generate_password_hash(password), user_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

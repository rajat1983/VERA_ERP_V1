import os

from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db_connection


def authenticate(email, password):
    email = (email or "").strip().lower()
    if not email or not password:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, email, username, password_hash, full_name, is_active
            FROM platform_users
            WHERE email=%s
            LIMIT 1
            """,
            (email,),
        )
        user = cur.fetchone()
        if not user or not user.get("is_active"):
            return None
        if not check_password_hash(user["password_hash"], password):
            return None
        return user
    finally:
        cur.close()
        conn.close()


def bootstrap_from_env():
    email = (os.environ.get("PLATFORM_BOOTSTRAP_EMAIL") or "").strip().lower()
    password = os.environ.get("PLATFORM_BOOTSTRAP_PASSWORD") or ""
    if not email or not password:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM platform_users LIMIT 1")
        if cur.fetchone():
            return None
        username = email.split("@")[0][:80] or "platform"
        cur.execute(
            """
            INSERT INTO platform_users (email, username, password_hash, full_name, is_active)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (email, username, generate_password_hash(password), "Platform admin"),
        )
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

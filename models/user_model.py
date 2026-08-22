from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection


def ensure_default_admin():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users LIMIT 1")
        if cur.fetchone():
            return
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            ("admin", generate_password_hash("admin123")),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def authenticate(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        if not user:
            return None
        if check_password_hash(user["password_hash"], password):
            return user
        return None
    finally:
        cur.close()
        conn.close()

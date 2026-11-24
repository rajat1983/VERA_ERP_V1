from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection


def _role_id(cur, name):
    cur.execute("SELECT id FROM roles WHERE name=%s", (name,))
    row = cur.fetchone()
    return row["id"] if row else None


def ensure_default_admin():
    """Do not insert hardcoded passwords. Existing users are left unchanged."""
    return


def _has_role_col(cur):
    cur.execute(
        """
        SELECT COUNT(*) AS c FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='users' AND COLUMN_NAME='role'
        """
    )
    return cur.fetchone()["c"] > 0


def _clean_profile(full_name, email, mobile, require_email=False):
    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()
    mobile = (mobile or "").strip()
    if not full_name:
        raise ValueError("Name is required.")
    if require_email and not email:
        raise ValueError("Email is required.")
    if email and "@" not in email:
        raise ValueError("Enter a valid email.")
    digits = "".join(ch for ch in mobile if ch.isdigit())
    if mobile and len(digits) < 10:
        raise ValueError("Enter a valid mobile number.")
    return full_name, email or None, mobile or None


def _assert_unique_email(cur, email, exclude_id=None, tenant_id=None):
    if not email:
        return
    sql = "SELECT id FROM users WHERE email=%s"
    params = [email]
    if tenant_id is not None:
        sql += " AND tenant_id=%s"
        params.append(tenant_id)
    if exclude_id:
        sql += " AND id <> %s"
        params.append(exclude_id)
    cur.execute(sql, params)
    if cur.fetchone():
        raise ValueError("That email is already in use.")


def _tenant_id_or_session(tenant_id=None):
    if tenant_id is not None:
        return int(tenant_id)
    from utils.tenant import current_tenant_id
    return current_tenant_id()


def authenticate(shop_code, identifier, password):
    from models.tenant_model import get_by_shop_code

    identifier = (identifier or "").strip()
    tenant = get_by_shop_code(shop_code)
    if not tenant or (tenant.get("status") or "").lower() != "active":
        return None
    if not identifier or not password:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT u.id, u.username, u.password_hash, u.is_active, u.role_id, u.status,
                   u.full_name, u.email, u.mobile, u.photo, u.tenant_id, r.name AS role
            FROM users u
            LEFT JOIN roles r ON r.id = u.role_id
            WHERE u.tenant_id=%s
              AND (u.username=%s OR (u.email IS NOT NULL AND u.email=%s))
            LIMIT 1
            """,
            (tenant["id"], identifier, identifier.lower()),
        )
        user = cur.fetchone()
        if not user:
            return None
        if not check_password_hash(user["password_hash"], password):
            return None
        user["role"] = (user.get("role") or "staff").lower()
        user["status"] = (user.get("status") or "active").lower()
        user["tenant"] = tenant
        return user
    finally:
        cur.close()
        conn.close()


def list_users():
    conn = get_db_connection()
    cur = conn.cursor()
    tenant_id = _tenant_id_or_session()
    cur.execute(
        """
        SELECT u.id, u.username, u.is_active, u.status, u.role_id, u.full_name, u.email, u.mobile, u.photo,
               r.name AS role, r.description AS role_description
        FROM users u
        LEFT JOIN roles r ON r.id = u.role_id
        WHERE u.tenant_id=%s
        ORDER BY FIELD(u.status, 'pending', 'approved', 'active', 'rejected'), u.id
        """,
        (tenant_id,),
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
        SELECT u.id, u.username, u.is_active, u.status, u.role_id, u.full_name, u.email, u.mobile, u.photo,
               u.tenant_id, r.name AS role
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
        WHERE r.name='admin' AND u.is_active=1 AND IFNULL(u.status, 'active')='active'
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


def create_user(username, password, role_id, is_active=1, full_name="", email="", mobile="", tenant_id=None):
    username = (username or "").strip()
    if not username or not password:
        raise ValueError("Username and password are required.")
    full_name, email, mobile = _clean_profile(full_name, email, mobile)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        tenant_id = int(tenant_id) if tenant_id is not None else _tenant_id_or_session()
        cur.execute(
            "SELECT id FROM users WHERE tenant_id=%s AND username=%s",
            (tenant_id, username),
        )
        if cur.fetchone():
            raise ValueError("Username already exists.")
        _assert_unique_email(cur, email, tenant_id=tenant_id)
        cur.execute("SELECT name FROM roles WHERE id=%s", (role_id,))
        role = cur.fetchone()
        if not role:
            raise ValueError("Invalid role.")
        cur.execute(
            """
            INSERT INTO users (tenant_id, username, password_hash, role_id, is_active, status, full_name, email, mobile)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tenant_id,
                username,
                generate_password_hash(password),
                role_id,
                1 if is_active else 0,
                "active" if is_active else "pending",
                full_name,
                email,
                mobile,
            ),
        )
        if _has_role_col(cur):
            cur.execute(
                "UPDATE users SET role=%s WHERE tenant_id=%s AND username=%s",
                (role["name"], tenant_id, username),
            )
        user_id = cur.lastrowid
        if not user_id:
            cur.execute(
                "SELECT id FROM users WHERE tenant_id=%s AND username=%s",
                (tenant_id, username),
            )
            user_id = cur.fetchone()["id"]
        conn.commit()
        return user_id
    except ValueError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_user(user_id, role_id, is_active, password=None, full_name="", email="", mobile=""):
    existing = get_user(user_id)
    if not existing:
        raise ValueError("User not found.")
    full_name, email, mobile = _clean_profile(full_name, email, mobile)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        _assert_unique_email(cur, email, exclude_id=user_id, tenant_id=existing.get("tenant_id"))
        cur.execute("SELECT name FROM roles WHERE id=%s", (role_id,))
        role = cur.fetchone()
        if not role:
            raise ValueError("Invalid role.")
        becoming_non_admin = role["name"] != "admin" or not is_active
        if existing.get("role") == "admin" and becoming_non_admin:
            if count_active_admins(exclude_id=user_id) < 1:
                raise ValueError("Keep at least one active admin.")
        status = "active" if is_active else (existing.get("status") or "pending")
        cur.execute(
            """
            UPDATE users
            SET role_id=%s, is_active=%s, status=%s, full_name=%s, email=%s, mobile=%s
            WHERE id=%s
            """,
            (role_id, 1 if is_active else 0, status, full_name, email, mobile, user_id),
        )
        if _has_role_col(cur):
            cur.execute("UPDATE users SET role=%s WHERE id=%s", (role["name"], user_id))
        if password:
            cur.execute(
                "UPDATE users SET password_hash=%s WHERE id=%s",
                (generate_password_hash(password), user_id),
            )
        conn.commit()
    except ValueError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def update_own_profile(user_id, full_name, email, mobile):
    if not get_user(user_id):
        raise ValueError("User not found.")
    full_name, email, mobile = _clean_profile(full_name, email, mobile)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        existing = get_user(user_id)
        _assert_unique_email(cur, email, exclude_id=user_id, tenant_id=(existing or {}).get("tenant_id"))
        cur.execute(
            "UPDATE users SET full_name=%s, email=%s, mobile=%s WHERE id=%s",
            (full_name, email, mobile, user_id),
        )
        conn.commit()
    except ValueError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
    return {"full_name": full_name, "email": email, "mobile": mobile}


def set_user_photo(user_id, filename):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET photo=%s WHERE id=%s", (filename, user_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def change_own_password(user_id, current_password, new_password):
    new_password = (new_password or "").strip()
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, password_hash FROM users WHERE id=%s", (user_id,))
        user = cur.fetchone()
        if not user:
            raise ValueError("User not found.")
        if not check_password_hash(user["password_hash"], current_password or ""):
            raise ValueError("Current password is incorrect.")
        cur.execute(
            "UPDATE users SET password_hash=%s WHERE id=%s",
            (generate_password_hash(new_password), user_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def login_blocked_reason(user):
    if not user:
        return "Invalid shop code, username, or password."
    status = (user.get("status") or "active").lower()
    if status == "pending":
        return "Your account is pending admin approval."
    if status == "rejected":
        return "Your registration was not approved."
    if user.get("is_active") in (0, "0", False):
        return "Invalid username or password."
    return None


def register_user(full_name, email, mobile, username, password, shop_code):
    from models.tenant_model import get_by_shop_code

    username = (username or "").strip()
    if not username or not password:
        raise ValueError("Username and password are required.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    tenant = get_by_shop_code(shop_code)
    if not tenant or (tenant.get("status") or "").lower() != "active":
        raise ValueError("Enter a valid shop code.")
    full_name, email, mobile = _clean_profile(full_name, email, mobile, require_email=True)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT id FROM users WHERE tenant_id=%s AND username=%s",
            (tenant["id"], username),
        )
        if cur.fetchone():
            raise ValueError("Username already exists.")
        _assert_unique_email(cur, email, tenant_id=tenant["id"])
        rid = _role_id(cur, "staff")
        if not rid:
            raise ValueError("Staff role is not set up.")
        cur.execute(
            """
            INSERT INTO users (tenant_id, username, password_hash, role_id, is_active, status, full_name, email, mobile)
            VALUES (%s, %s, %s, %s, 0, 'pending', %s, %s, %s)
            """,
            (tenant["id"], username, generate_password_hash(password), rid, full_name, email, mobile),
        )
        if _has_role_col(cur):
            cur.execute(
                "UPDATE users SET role='staff' WHERE tenant_id=%s AND username=%s",
                (tenant["id"], username),
            )
        conn.commit()
        cur.execute(
            "SELECT id FROM users WHERE tenant_id=%s AND username=%s",
            (tenant["id"], username),
        )
        row = cur.fetchone()
        return {
            "id": row["id"],
            "username": username,
            "full_name": full_name,
            "email": email,
        }
    except ValueError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def approve_registration(user_id):
    user = get_user(user_id)
    if not user:
        raise ValueError("User not found.")
    if (user.get("status") or "").lower() not in ("pending", "approved"):
        raise ValueError("This account is not waiting for approval.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE users
            SET status='active', is_active=1, activation_token=NULL, activation_expires=NULL
            WHERE id=%s
            """,
            (user_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return get_user(user_id)


def reject_registration(user_id):
    user = get_user(user_id)
    if not user:
        raise ValueError("User not found.")
    if (user.get("status") or "").lower() not in ("pending", "approved"):
        raise ValueError("This account cannot be rejected.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE users
            SET status='rejected', is_active=0, activation_token=NULL, activation_expires=NULL
            WHERE id=%s
            """,
            (user_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def activate_by_token(token):
    token = (token or "").strip()
    if not token:
        raise ValueError("Invalid activation link.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, status, activation_expires
            FROM users
            WHERE activation_token=%s
            """,
            (token,),
        )
        user = cur.fetchone()
        if not user:
            raise ValueError("This activation link is invalid or has already been used.")
        expires = user.get("activation_expires")
        if expires and expires < datetime.now():
            raise ValueError("This activation link has expired. Ask an admin to approve again.")
        if (user.get("status") or "").lower() != "approved":
            raise ValueError("This account cannot be activated.")
        cur.execute(
            """
            UPDATE users
            SET status='active', is_active=1, activation_token=NULL, activation_expires=NULL
            WHERE id=%s
            """,
            (user["id"],),
        )
        conn.commit()
    except ValueError:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

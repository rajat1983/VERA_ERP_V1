import time
from flask import request, session

from db import get_db_connection


_FAILS = {}
LOCK_AFTER = 5
LOCK_SECONDS = 15 * 60


def _fail_key():
    ip = (request.remote_addr or "unknown").strip()
    shop = (request.form.get("shop_code") or "").strip().upper()
    user = (request.form.get("username") or "").strip().lower()
    return f"{ip}:{shop}:{user}"


def is_locked():
    rec = _FAILS.get(_fail_key())
    if not rec:
        return False
    if rec["count"] < LOCK_AFTER:
        return False
    if time.time() < rec["until"]:
        return True
    _FAILS.pop(_fail_key(), None)
    return False


def record_failure():
    key = _fail_key()
    rec = _FAILS.get(key) or {"count": 0, "until": 0}
    rec["count"] += 1
    if rec["count"] >= LOCK_AFTER:
        rec["until"] = time.time() + LOCK_SECONDS
    _FAILS[key] = rec


def clear_failures():
    _FAILS.pop(_fail_key(), None)


def write_audit(action, module, entity=None, entity_id=None, detail=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO audit_log (user_id, username, action, module, entity, entity_id, detail, ip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session.get("user_id"),
                session.get("username"),
                action,
                module,
                entity,
                entity_id,
                (detail or "")[:500],
                (request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:45],
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

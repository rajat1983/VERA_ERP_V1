from db import get_db_connection

KEYS = (
    "default_grace_days",
    "razorpay_key_id",
    "razorpay_key_secret",
    "razorpay_webhook_secret",
    "platform_gstin",
    "support_email",
)

SECRET_KEYS = {"razorpay_key_secret", "razorpay_webhook_secret"}


def get_all():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT setting_key, setting_value FROM platform_settings")
        rows = {r["setting_key"]: r["setting_value"] for r in cur.fetchall()}
        return {key: rows.get(key, "") for key in KEYS}
    finally:
        cur.close()
        conn.close()


def get_value(key, default=""):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT setting_value FROM platform_settings WHERE setting_key=%s",
            (key,),
        )
        row = cur.fetchone()
        return (row["setting_value"] if row else default) or default
    finally:
        cur.close()
        conn.close()


def save(values):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        current = get_all()
        for key in KEYS:
            value = values.get(key)
            if key in SECRET_KEYS and not (value or "").strip():
                value = current.get(key) or ""
            cur.execute(
                """
                INSERT INTO platform_settings (setting_key, setting_value)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value)
                """,
                (key, str(value or "")),
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def razorpay_configured():
    key_id = (get_value("razorpay_key_id") or "").strip()
    secret = (get_value("razorpay_key_secret") or "").strip()
    return bool(key_id and secret)

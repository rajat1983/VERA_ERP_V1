from datetime import date, timedelta

from db import get_db_connection


def _grace_days(cur, override=None):
    if override is not None:
        return int(override)
    cur.execute(
        "SELECT setting_value FROM platform_settings WHERE setting_key='default_grace_days' LIMIT 1"
    )
    row = cur.fetchone()
    try:
        return int(row["setting_value"]) if row else 7
    except (TypeError, ValueError):
        return 7


def list_plans(public_only=False, include_inactive=False):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        sql = "SELECT * FROM subscription_plans WHERE 1=1"
        if not include_inactive:
            sql += " AND is_active=1"
        if public_only:
            sql += " AND is_public=1"
        sql += " ORDER BY duration_days"
        cur.execute(sql)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_plan(plan_id):
    try:
        plan_id = int(plan_id)
    except (TypeError, ValueError):
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM subscription_plans WHERE id=%s", (plan_id,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def update_plan(
    plan_id,
    name,
    duration_days,
    price_paise,
    gst_rate,
    max_users,
    is_public,
    is_active,
    allow_pos=True,
    allow_production=True,
    allow_services=True,
    extra_user_price_paise=0,
):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE subscription_plans
            SET name=%s, duration_days=%s, price_paise=%s, gst_rate=%s,
                max_users=%s, is_public=%s, is_active=%s,
                allow_pos=%s, allow_production=%s, allow_services=%s,
                extra_user_price_paise=%s
            WHERE id=%s
            """,
            (
                (name or "").strip(),
                int(duration_days),
                int(price_paise),
                float(gst_rate),
                int(max_users),
                1 if is_public else 0,
                1 if is_active else 0,
                1 if allow_pos else 0,
                1 if allow_production else 0,
                1 if allow_services else 0,
                max(0, int(extra_user_price_paise or 0)),
                plan_id,
            ),
        )
        if cur.rowcount == 0:
            raise ValueError("Plan not found.")
        conn.commit()
    except ValueError:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def get_for_tenant(tenant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT s.*, p.code AS plan_code, p.name AS plan_name, p.duration_days, p.price_paise,
                   p.max_users AS included_users, p.allow_pos, p.allow_production, p.allow_services,
                   p.extra_user_price_paise AS plan_extra_user_price_paise
            FROM subscriptions s
            JOIN subscription_plans p ON p.id = s.plan_id
            WHERE s.tenant_id=%s
            LIMIT 1
            """,
            (tenant_id,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def list_events(tenant_id, limit=20):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT event_type, notes, created_at
            FROM subscription_events
            WHERE tenant_id=%s
            ORDER BY id DESC
            LIMIT %s
            """,
            (tenant_id, int(limit)),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def _add_event(cur, tenant_id, subscription_id, event_type, notes=""):
    cur.execute(
        """
        INSERT INTO subscription_events (tenant_id, subscription_id, event_type, notes)
        VALUES (%s, %s, %s, %s)
        """,
        (tenant_id, subscription_id, event_type, (notes or "")[:255]),
    )


def ensure_pending(tenant_id, plan_id):
    plan = get_plan(plan_id)
    if not plan or not plan.get("is_active"):
        raise ValueError("Choose a valid plan.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        grace = _grace_days(cur)
        cur.execute(
            """
            INSERT INTO subscriptions (tenant_id, plan_id, status, grace_days)
            VALUES (%s, %s, 'pending', %s)
            ON DUPLICATE KEY UPDATE plan_id=VALUES(plan_id), status='pending'
            """,
            (tenant_id, plan_id, grace),
        )
        cur.execute("SELECT id FROM subscriptions WHERE tenant_id=%s", (tenant_id,))
        sub = cur.fetchone()
        _add_event(cur, tenant_id, sub["id"], "pending", f"Plan {plan['code']}")
        conn.commit()
        return get_for_tenant(tenant_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def activate(tenant_id, plan_id=None, note="Activated"):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM subscriptions WHERE tenant_id=%s LIMIT 1", (tenant_id,))
        sub = cur.fetchone()
        plan_id = int(plan_id or (sub["plan_id"] if sub else 0))
        cur.execute("SELECT * FROM subscription_plans WHERE id=%s", (plan_id,))
        plan = cur.fetchone()
        if not plan:
            raise ValueError("Plan not found.")
        today = date.today()
        ends = today + timedelta(days=int(plan["duration_days"]))
        grace = _grace_days(cur, sub["grace_days"] if sub else None)
        if sub:
            cur.execute(
                """
                UPDATE subscriptions
                SET plan_id=%s, status='active', starts_on=%s, ends_on=%s, grace_days=%s
                WHERE id=%s
                """,
                (plan_id, today, ends, grace, sub["id"]),
            )
            sub_id = sub["id"]
        else:
            cur.execute(
                """
                INSERT INTO subscriptions (tenant_id, plan_id, status, starts_on, ends_on, grace_days)
                VALUES (%s, %s, 'active', %s, %s, %s)
                """,
                (tenant_id, plan_id, today, ends, grace),
            )
            sub_id = cur.lastrowid
        _add_event(cur, tenant_id, sub_id, "activate", note)
        conn.commit()
        return get_for_tenant(tenant_id)
    except ValueError:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def apply_paid(tenant_id, plan_id, note="Payment"):
    current = access(tenant_id)
    if current.get("allowed") and current.get("status") in ("active", "grace"):
        return extend(tenant_id, note=note, plan_id=plan_id)
    return activate(tenant_id, plan_id, note=note)


def extend(tenant_id, note="Extended", plan_id=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT s.*, p.duration_days
            FROM subscriptions s
            JOIN subscription_plans p ON p.id = s.plan_id
            WHERE s.tenant_id=%s
            LIMIT 1
            """,
            (tenant_id,),
        )
        sub = cur.fetchone()
        if not sub:
            raise ValueError("No subscription to extend.")
        if plan_id:
            cur.execute("SELECT duration_days FROM subscription_plans WHERE id=%s", (plan_id,))
            plan = cur.fetchone()
            if not plan:
                raise ValueError("Plan not found.")
            duration = int(plan["duration_days"])
        else:
            duration = int(sub["duration_days"])
            plan_id = sub["plan_id"]
        today = date.today()
        current_end = sub.get("ends_on") or today
        base = current_end if current_end and current_end > today else today
        ends = base + timedelta(days=duration)
        cur.execute(
            """
            UPDATE subscriptions
            SET plan_id=%s, status='active', ends_on=%s, starts_on=IFNULL(starts_on, %s)
            WHERE id=%s
            """,
            (plan_id, ends, today, sub["id"]),
        )
        _add_event(cur, tenant_id, sub["id"], "extend", note)
        conn.commit()
        return get_for_tenant(tenant_id)
    except ValueError:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def set_subscription_status(tenant_id, status, note=""):
    status = (status or "").strip().lower()
    if status not in ("pending", "active", "grace", "expired", "suspended", "cancelled"):
        raise ValueError("Invalid subscription status.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM subscriptions WHERE tenant_id=%s LIMIT 1", (tenant_id,))
        sub = cur.fetchone()
        if not sub:
            raise ValueError("No subscription.")
        cur.execute("UPDATE subscriptions SET status=%s WHERE id=%s", (status, sub["id"]))
        _add_event(cur, tenant_id, sub["id"], status, note)
        conn.commit()
    except ValueError:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def extra_seat_charge_paise(extra_users, price_paise):
    extra_users = max(0, int(extra_users or 0))
    return extra_users * max(0, int(price_paise or 0))


def effective_user_limit(included_users, extra_users):
    return max(0, int(included_users or 0)) + max(0, int(extra_users or 0))


def resolve_extra_user_price(shop_price_paise, plan_price_paise):
    if shop_price_paise is None or shop_price_paise == "":
        return max(0, int(plan_price_paise or 0))
    return max(0, int(shop_price_paise))


def set_extra_seats(tenant_id, extra_users, extra_user_price_paise=None):
    extra_users = int(extra_users)
    if extra_users < 0:
        raise ValueError("Extra users cannot be negative.")
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM subscriptions WHERE tenant_id=%s LIMIT 1", (tenant_id,))
        sub = cur.fetchone()
        if not sub:
            raise ValueError("Activate a plan for this shop before adding extra users.")
        if extra_user_price_paise is None or extra_user_price_paise == "":
            price = None
        else:
            price = max(0, int(round(float(extra_user_price_paise))))
        cur.execute(
            """
            UPDATE subscriptions
            SET extra_users=%s, extra_user_price_paise=%s
            WHERE id=%s
            """,
            (extra_users, price, sub["id"]),
        )
        _add_event(
            cur,
            tenant_id,
            sub["id"],
            "seats",
            f"Extra users {extra_users}" + ("" if price is None else f", ₹{price / 100:.0f}/user"),
        )
        conn.commit()
        return access(tenant_id)
    except ValueError:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def evaluate_status(status, ends_on, grace_days, today=None):
    today = today or date.today()
    status = (status or "pending").lower()
    grace = int(grace_days or 7)
    if status in ("suspended", "cancelled", "pending"):
        return status, False
    if ends_on is None:
        return status, status == "active"
    if today <= ends_on:
        return "active", True
    if today <= ends_on + timedelta(days=grace):
        return "grace", True
    return "expired", False


def access(tenant_id):
    """Return access dict. Mutates expired/grace based on dates."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT s.*, p.code AS plan_code, p.name AS plan_name, p.duration_days,
                   p.max_users AS included_users, p.allow_pos, p.allow_production, p.allow_services,
                   p.extra_user_price_paise AS plan_extra_user_price_paise
            FROM subscriptions s
            JOIN subscription_plans p ON p.id = s.plan_id
            WHERE s.tenant_id=%s
            LIMIT 1
            """,
            (tenant_id,),
        )
        sub = cur.fetchone()
        if not sub:
            return {
                "allowed": False,
                "status": "pending",
                "plan_name": None,
                "ends_on": None,
                "included_users": 5,
                "extra_users": 0,
                "extra_user_price_paise": 0,
                "extra_charge_paise": 0,
                "max_users": 5,
                "allow_pos": True,
                "allow_production": True,
                "allow_services": True,
                "message": "No subscription. Ask Super Admin to activate a plan.",
            }
        today = date.today()
        ends = sub.get("ends_on")
        grace = int(sub.get("grace_days") or 7)
        stored = (sub.get("status") or "pending").lower()
        status, allowed = evaluate_status(stored, ends, grace, today)
        if status != stored and stored not in ("suspended", "cancelled", "pending"):
            cur.execute("UPDATE subscriptions SET status=%s WHERE id=%s", (status, sub["id"]))
            conn.commit()
        messages = {
            "pending": "This shop is waiting for Super Admin to activate a plan.",
            "grace": f"Subscription ended {ends}. ERP stays open until {ends + timedelta(days=grace) if ends else ''} (grace).",
            "expired": "Subscription has ended. Ask Super Admin to extend or mark paid.",
            "suspended": "Subscription is suspended.",
            "cancelled": "Subscription is cancelled.",
            "active": None,
        }
        included = int(sub.get("included_users") or 5)
        extra = int(sub.get("extra_users") or 0)
        extra_price = resolve_extra_user_price(
            sub.get("extra_user_price_paise"),
            sub.get("plan_extra_user_price_paise"),
        )
        return {
            "allowed": allowed,
            "status": status,
            "plan_name": sub.get("plan_name"),
            "plan_code": sub.get("plan_code"),
            "starts_on": sub.get("starts_on"),
            "ends_on": ends,
            "grace_days": grace,
            "message": messages.get(status),
            "subscription_id": sub["id"],
            "included_users": included,
            "extra_users": extra,
            "extra_user_price_paise": extra_price,
            "plan_extra_user_price_paise": int(sub.get("plan_extra_user_price_paise") or 0),
            "extra_charge_paise": extra_seat_charge_paise(extra, extra_price),
            "max_users": effective_user_limit(included, extra),
            "allow_pos": bool(sub.get("allow_pos", 1)),
            "allow_production": bool(sub.get("allow_production", 1)),
            "allow_services": bool(sub.get("allow_services", 1)),
        }
    finally:
        cur.close()
        conn.close()


def format_price(paise):
    rupees = int(paise or 0) / 100.0
    return f"₹{rupees:,.0f}"

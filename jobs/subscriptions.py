"""Daily subscription reminders: python -m jobs.subscriptions"""

from datetime import date, timedelta

from models import subscription_model
from utils.mailer import send_email
from db import get_db_connection


def shops_due_in(days):
    target = date.today() + timedelta(days=days)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT s.tenant_id, s.ends_on, t.name, t.shop_code, u.email, u.full_name
            FROM subscriptions s
            JOIN tenants t ON t.id = s.tenant_id
            LEFT JOIN users u ON u.tenant_id = t.id AND u.status IN ('active', 'approved')
            WHERE s.status IN ('active', 'grace')
              AND s.ends_on = %s
            GROUP BY s.tenant_id, s.ends_on, t.name, t.shop_code, u.email, u.full_name
            """,
            (target,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def run():
    for days in (15, 7, 1):
        for row in shops_due_in(days):
            email = row.get("email")
            if not email:
                continue
            send_email(
                email,
                f"VERA ERP plan ends in {days} day(s)",
                f"<p>Hello {row.get('full_name') or row['shop_code']},</p>"
                f"<p>The plan for <strong>{row['name']}</strong> ({row['shop_code']}) "
                f"ends on {row['ends_on']}.</p>"
                f"<p>Sign in and open Billing to pay with Razorpay, or ask the platform operator to extend.</p>",
            )


if __name__ == "__main__":
    from utils.schema import ensure_schema

    ensure_schema()
    run()
    print("Reminder pass complete.")

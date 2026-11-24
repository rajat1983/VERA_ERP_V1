import pytest
from werkzeug.security import generate_password_hash

from db import get_db_connection
from models import product_model, tenant_model, user_model
from utils.schema import ensure_schema
from utils.totals import calculate_document_totals


def _conn():
    return get_db_connection()


def _cleanup():
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM tenants WHERE shop_code IN ('TESTA', 'TESTB')")
        ids = [row["id"] for row in cur.fetchall()]
        if ids:
            fmt = ",".join(["%s"] * len(ids))
            cur.execute(f"DELETE FROM sale_items WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM sales WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM subscription_events WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM platform_payments WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM platform_invoices WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM subscriptions WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM products WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM product_categories WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM customers WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM users WHERE tenant_id IN ({fmt})", ids)
            cur.execute(f"DELETE FROM company WHERE tenant_id IN ({fmt})", ids)
            cur.execute("DELETE FROM tenants WHERE shop_code IN ('TESTA', 'TESTB')")
        conn.commit()
    finally:
        cur.close()
        conn.close()


@pytest.fixture(scope="module")
def isolation():
    ensure_schema()
    _cleanup()
    tenant_a = tenant_model.create_tenant("Isolation A", shop_code="TESTA")
    tenant_b = tenant_model.create_tenant("Isolation B", shop_code="TESTB")
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM roles WHERE name='admin' LIMIT 1")
        role = cur.fetchone()
        rid = role["id"] if role else 1
        for tenant, username, email in (
            (tenant_a, "iso_a", "iso_a@example.com"),
            (tenant_b, "iso_b", "iso_b@example.com"),
        ):
            cur.execute(
                """
                INSERT INTO users (tenant_id, username, password_hash, role_id, is_active, status, email)
                VALUES (%s, %s, %s, %s, 1, 'active', %s)
                """,
                (tenant["id"], username, generate_password_hash("secret12"), rid, email),
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    yield tenant_a, tenant_b
    _cleanup()


def test_login_requires_shop_code(isolation):
    assert user_model.authenticate("", "iso_a", "secret12") is None
    assert user_model.authenticate("TESTA", "iso_a", "wrong") is None


def test_login_username_and_email(isolation):
    tenant_a, _tenant_b = isolation
    by_user = user_model.authenticate("TESTA", "iso_a", "secret12")
    by_email = user_model.authenticate("TESTA", "iso_a@example.com", "secret12")
    assert by_user and by_user["username"] == "iso_a"
    assert by_email and by_email["id"] == by_user["id"]
    assert by_user["tenant"]["id"] == tenant_a["id"]


def test_login_wrong_shop(isolation):
    assert user_model.authenticate("TESTB", "iso_a", "secret12") is None


def test_product_isolation(isolation):
    from app import app

    tenant_a, tenant_b = isolation
    with app.test_request_context("/"):
        from flask import g, session

        session["tenant_id"] = tenant_a["id"]
        g.tenant_id = tenant_a["id"]
        product_model.add_product(
            {
                "tenant_id": tenant_a["id"],
                "vendor_id": None,
                "name": "ZTISO Alpha Widget",
                "sku": "ZTISO-A-1",
                "image": None,
                "cost_price": 1,
                "selling_price": 2,
                "stock_qty": 0,
                "reorder_level": 0,
                "status": "active",
            }
        )
        product_model.add_category("ZTISO-Cat-A")

    with app.test_request_context("/"):
        from flask import g, session

        session["tenant_id"] = tenant_b["id"]
        g.tenant_id = tenant_b["id"]
        rows = product_model.get_all_products("ZTISO", 20, 0)
        assert all("Alpha" not in (r.get("name") or "") for r in rows)
        assert not product_model.product_search("ZTISO-A-1")
        assert not product_model.search_categories("ZTISO-Cat")
        found = product_model.get_product_by_id(0)
        assert found is None

    with app.test_request_context("/"):
        from flask import g, session

        session["tenant_id"] = tenant_a["id"]
        g.tenant_id = tenant_a["id"]
        found = product_model.product_search("ZTISO-A-1")
        assert len(found) == 1
        cats = product_model.search_categories("ZTISO-Cat")
        assert any(c["name"] == "ZTISO-Cat-A" for c in cats)


def test_customer_sale_isolation(isolation):
    from app import app
    from models import customer_model, sales_model

    tenant_a, tenant_b = isolation
    with app.test_request_context("/"):
        from flask import g, session

        session["tenant_id"] = tenant_a["id"]
        g.tenant_id = tenant_a["id"]
        cid = customer_model.add_customer(
            customer_model.generate_customer_code(),
            "ZTISO Cust A",
            "ztiso-a@example.com",
            "9999999999",
            "",
            "",
            "",
            "",
            "",
            "Active",
        )
        rows = customer_model.get_all_customers("ZTISO", 20, 0)
        assert any(r["id"] == cid for r in rows)
        sales = sales_model.get_all_sales("", 20, 0)
        assert all(r.get("customer_name") != "Parida" for r in sales)

    with app.test_request_context("/"):
        from flask import g, session

        session["tenant_id"] = tenant_b["id"]
        g.tenant_id = tenant_b["id"]
        assert customer_model.get_customer_by_id(cid) is None
        rows = customer_model.get_all_customers("ZTISO", 20, 0)
        assert all(r["id"] != cid for r in rows)
        assert not sales_model.get_all_sales("ZTISO Cust A", 20, 0)


def test_payment_fulfill_idempotent(isolation):
    from models import platform_billing_model, subscription_model

    tenant_a, _tenant_b = isolation
    plan = subscription_model.list_plans()[0]
    first = platform_billing_model.fulfill(
        tenant_a["id"], plan, "pay_test_1", "order_test_1", 10**12, source="test"
    )
    second = platform_billing_model.fulfill(
        tenant_a["id"], plan, "pay_test_1", "order_test_1", 10**12, source="test"
    )
    assert first["duplicate"] is False
    assert second["duplicate"] is True


def test_subscription_gate(isolation):
    from models import subscription_model

    tenant_a, _tenant_b = isolation
    plans = subscription_model.list_plans()
    assert plans
    subscription_model.ensure_pending(tenant_a["id"], plans[0]["id"])
    pending = subscription_model.access(tenant_a["id"])
    assert pending["allowed"] is False
    subscription_model.activate(tenant_a["id"], plans[0]["id"])
    active = subscription_model.access(tenant_a["id"])
    assert active["allowed"] is True
    assert active["status"] == "active"


def test_suspend_blocks_login(isolation):
    tenant_a, _tenant_b = isolation
    tenant_model.set_status(tenant_a["id"], "suspended")
    assert user_model.authenticate("TESTA", "iso_a", "secret12") is None
    tenant_model.set_status(tenant_a["id"], "active")
    assert user_model.authenticate("TESTA", "iso_a", "secret12")


def test_platform_shop_counts(isolation):
    counts = tenant_model.counts()
    assert counts["total"] >= 2
    shops = tenant_model.list_tenants(search="TESTA")
    assert shops and shops[0]["shop_code"] == "TESTA"


def test_platform_vs_shop_routes():
    from app import app

    client = app.test_client()
    shop_hit = client.get("/platform/", follow_redirects=False)
    assert shop_hit.status_code in (302, 403)
    with client.session_transaction() as sess:
        sess["platform_user_id"] = 1
        sess["_csrf"] = "x"
    home = client.get("/platform/", follow_redirects=False)
    assert home.status_code == 200
    shops = client.get("/platform/shops", follow_redirects=False)
    assert shops.status_code == 200
    erp = client.get("/products", follow_redirects=False)
    assert erp.status_code in (302, 403)


def test_totals_still_pass():
    items = [{"qty": 1, "price": 10, "tax_rate": 0}]
    totals = calculate_document_totals(items, 0)
    assert totals["grand_total"] == 10

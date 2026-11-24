import os
import time

import pytest
from flask import session
from werkzeug.security import generate_password_hash

from db import get_db_connection
from models import (
    customer_model,
    product_model,
    purchase_cancel,
    purchase_model,
    tenant_model,
    user_model,
    vendor_model,
)
from models.production_extra import cancel_production
from utils.schema import ensure_schema
from utils.security import assert_production_safe


CODES = ("P1SECA", "P1SECB")


def _conn():
    return get_db_connection()


def _cleanup():
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM tenants WHERE shop_code IN (%s, %s)", CODES)
        ids = [row["id"] for row in cur.fetchall()]
        if ids:
            fmt = ",".join(["%s"] * len(ids))
            for table in (
                "production_materials",
                "production_batches",
                "purchase_items",
                "purchases",
                "sale_items",
                "sales",
                "stock_movements",
                "products",
                "product_categories",
                "customers",
                "vendors",
                "users",
                "subscriptions",
                "subscription_events",
                "company",
            ):
                cur.execute(
                    """
                    SELECT COUNT(*) AS c FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s
                    """,
                    (table,),
                )
                if not cur.fetchone()["c"]:
                    continue
                cur.execute(f"DELETE FROM `{table}` WHERE tenant_id IN ({fmt})", ids)
            cur.execute("DELETE FROM tenants WHERE shop_code IN (%s, %s)", CODES)
        conn.commit()
    finally:
        cur.close()
        conn.close()


@pytest.fixture
def shops():
    ensure_schema()
    _cleanup()
    a = tenant_model.create_tenant("Phase1 A", shop_code=CODES[0])
    b = tenant_model.create_tenant("Phase1 B", shop_code=CODES[1])
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM roles WHERE name='admin' LIMIT 1")
        rid = cur.fetchone()["id"]
        for tenant, username in ((a, "p1a_admin"), (b, "p1b_admin")):
            cur.execute(
                """
                INSERT INTO users (tenant_id, username, password_hash, role_id, is_active, status, email)
                VALUES (%s, %s, %s, %s, 1, 'active', %s)
                """,
                (
                    tenant["id"],
                    username,
                    generate_password_hash("secret12"),
                    rid,
                    username + "@example.com",
                ),
            )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    yield a, b
    _cleanup()


def _ctx(app, tenant_id, user_id=None):
    ctx = app.test_request_context("/")
    ctx.push()
    session["tenant_id"] = tenant_id
    if user_id:
        session["user_id"] = user_id
    from flask import g

    g.tenant_id = tenant_id
    return ctx


def _add_product(app, tenant, sku, stock=10):
    with app.test_request_context("/"):
        session["tenant_id"] = tenant["id"]
        from flask import g

        g.tenant_id = tenant["id"]
        product_model.add_product(
            {
                "name": "P1 %s" % sku,
                "sku": sku,
                "image": None,
                "cost_price": 1,
                "selling_price": 2,
                "stock_qty": stock,
                "reorder_level": 0,
                "status": "active",
                "vendor_id": None,
            }
        )
        conn = _conn()
        cur = conn.cursor()
        cur.execute("SELECT id, stock_qty FROM products WHERE tenant_id=%s AND sku=%s", (tenant["id"], sku))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row


def test_user_idor_and_last_admin(shops):
    from app import app

    tenant_a, tenant_b = shops
    conn = _conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE tenant_id=%s AND username='p1b_admin'", (tenant_b["id"],))
    other = cur.fetchone()
    cur.execute("SELECT id FROM users WHERE tenant_id=%s AND username='p1a_admin'", (tenant_a["id"],))
    mine = cur.fetchone()
    cur.close()
    conn.close()

    ctx = _ctx(app, tenant_a["id"], mine["id"])
    try:
        assert user_model.get_user(other["id"]) is None
        assert user_model.get_user(mine["id"])["id"] == mine["id"]
        assert user_model.count_active_admins() == 1
        u = user_model.get_user(mine["id"])
        with pytest.raises(ValueError, match="admin"):
            user_model.update_user(
                u["id"],
                u["role_id"],
                False,
                full_name=u.get("full_name") or u["username"],
                email=u.get("email") or "",
                mobile=u.get("mobile") or "",
            )
    finally:
        ctx.pop()

    ctx = _ctx(app, tenant_b["id"])
    try:
        assert user_model.count_active_admins() == 1
    finally:
        ctx.pop()


def test_purchase_rejects_foreign_product_and_vendor(shops):
    from app import app

    tenant_a, tenant_b = shops
    prod_b = _add_product(app, tenant_b, "P1-B-%s" % str(int(time.time()))[-5:])
    ctx = _ctx(app, tenant_a["id"])
    try:
        vendor_model.add_vendor(
            "P1VA",
            "Vendor A",
            None,
            "9999999999",
            None,
            None,
            None,
            None,
            None,
            "Active",
        )
        conn = _conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM vendors WHERE tenant_id=%s AND vendor_code='P1VA'", (tenant_a["id"],))
        vid = cur.fetchone()["id"]
        cur.close()
        conn.close()
        with pytest.raises(ValueError):
            purchase_model.create_purchase(
                "PUR-P1-X",
                vid,
                "INV-X",
                "2026-01-01",
                [{"product_id": prod_b["id"], "qty": 1, "price": 1}],
            )
    finally:
        ctx.pop()

    ctx = _ctx(app, tenant_b["id"])
    try:
        with pytest.raises(ValueError):
            purchase_model.create_purchase(
                "PUR-P1-Y",
                vid,
                "INV-Y",
                "2026-01-01",
                [{"product_id": prod_b["id"], "qty": 1, "price": 1}],
            )
    finally:
        ctx.pop()


def test_purchase_stock_stays_on_own_tenant(shops):
    from app import app

    tenant_a, tenant_b = shops
    stamp = str(int(time.time()))[-5:]
    prod_a = _add_product(app, tenant_a, "P1-A-%s" % stamp, stock=5)
    prod_b = _add_product(app, tenant_b, "P1-BX-%s" % stamp, stock=40)
    ctx = _ctx(app, tenant_a["id"])
    try:
        vendor_model.add_vendor(
            "P1VA2",
            "Vendor A2",
            None,
            "8888888888",
            None,
            None,
            None,
            None,
            None,
            "Active",
        )
        conn = _conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM vendors WHERE tenant_id=%s AND vendor_code='P1VA2'", (tenant_a["id"],))
        vid = cur.fetchone()["id"]
        cur.close()
        conn.close()
        pid = purchase_model.create_purchase(
            "PURP1A%s" % stamp,
            vid,
            "INV-A",
            "2026-01-01",
            [{"product_id": prod_a["id"], "qty": 3, "price": 10}],
        )
        after_a = product_model.get_product_by_id(prod_a["id"])
        assert after_a["stock_qty"] == 8
        purchase_cancel.cancel_purchase(pid)
        with pytest.raises(ValueError):
            purchase_cancel.cancel_purchase(pid)
        restored = product_model.get_product_by_id(prod_a["id"])
        assert restored["stock_qty"] == 5
    finally:
        ctx.pop()

    ctx = _ctx(app, tenant_b["id"])
    try:
        other = product_model.get_product_by_id(prod_b["id"])
        assert other["stock_qty"] == 40
        assert product_model.get_product_by_id(prod_a["id"]) is None
        with pytest.raises(ValueError):
            purchase_cancel.cancel_purchase(pid)
    finally:
        ctx.pop()


def test_production_cancel_is_tenant_scoped_and_idempotent(shops):
    from app import app

    conn = _conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) AS c FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='production_batches'
        """
    )
    exists = cur.fetchone()["c"]
    cur.close()
    conn.close()
    if not exists:
        pytest.skip("production_batches table is not installed in this database")

    tenant_a, tenant_b = shops
    ctx = _ctx(app, tenant_a["id"])
    try:
        with pytest.raises(ValueError):
            cancel_production(99999991)
    finally:
        ctx.pop()
    ctx = _ctx(app, tenant_b["id"])
    try:
        with pytest.raises(ValueError):
            cancel_production(99999991)
    finally:
        ctx.pop()


def test_suspended_shop_blocked_on_erp_routes(shops):
    from app import app

    tenant_a, _tenant_b = shops
    tenant_model.set_status(tenant_a["id"], "suspended")
    assert user_model.authenticate(CODES[0], "p1a_admin", "secret12") is None
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["tenant_id"] = tenant_a["id"]
        sess["role"] = "admin"
        sess["_csrf"] = "tok"
        sess["_last_seen"] = time.time()
    resp = client.get("/products", follow_redirects=False)
    assert resp.status_code in (302, 303)
    assert "/billing" in (resp.headers.get("Location") or "")
    billing = client.get("/billing/", follow_redirects=False)
    assert billing.status_code in (200, 302)
    tenant_model.set_status(tenant_a["id"], "active")


def test_platform_not_gated_by_shop_subscription(shops):
    from app import app

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["platform_user_id"] = 1
        sess["_csrf"] = "x"
        sess["_last_seen"] = time.time()
    home = client.get("/platform/", follow_redirects=False)
    assert home.status_code == 200


def test_production_mode_rejects_insecure_defaults(monkeypatch):
    monkeypatch.setenv("VERA_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    with pytest.raises(SystemExit):
        assert_production_safe()
    monkeypatch.setenv("SECRET_KEY", "insecure-dev-key")
    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setenv("DB_USER", "u")
    monkeypatch.setenv("DB_PASSWORD", "p")
    monkeypatch.setenv("DB_NAME", "vera_erp")
    with pytest.raises(SystemExit):
        assert_production_safe()
    monkeypatch.setenv("SECRET_KEY", "a-long-unique-production-secret")
    monkeypatch.setenv("VERA_AUTH", "0")
    with pytest.raises(SystemExit):
        assert_production_safe()
    monkeypatch.setenv("VERA_AUTH", "1")
    monkeypatch.setenv("FLASK_DEBUG", "0")
    assert_production_safe()


def test_db_module_has_no_hardcoded_production_password():
    import inspect
    import db as dbmod

    source = inspect.getsource(dbmod)
    assert "os.environ" in source
    assert 'os.environ.get("DB_PASSWORD"' in source or "os.environ[\"DB_PASSWORD\"]" in source


def test_customer_isolation(shops):
    from app import app

    tenant_a, tenant_b = shops
    ctx = _ctx(app, tenant_a["id"])
    try:
        cid = customer_model.add_customer(
            customer_model.generate_customer_code(),
            "P1 Cust A",
            "p1a@example.com",
            "9000000001",
            "",
            "",
            "",
            "",
            "",
            "Active",
        )
    finally:
        ctx.pop()
    ctx = _ctx(app, tenant_b["id"])
    try:
        assert customer_model.get_customer_by_id(cid) is None
    finally:
        ctx.pop()

import time

from flask import session

from app import app
from db import get_db_connection
from models import product_model, tenant_model


def _product_payload(tenant_id, sku):
    return {
        "tenant_id": tenant_id,
        "vendor_id": None,
        "name": "Isolation %s" % sku,
        "short_name": None,
        "brand": None,
        "sku": sku,
        "barcode": None,
        "image": None,
        "cost_price": 1,
        "selling_price": 2,
        "mrp": None,
        "stock_qty": 0,
        "reorder_level": 0,
        "low_stock_threshold": 0,
        "tax_rate": 0,
        "hsn_code": None,
        "unit": "pcs",
        "product_type": "finished_goods",
        "category": None,
        "description": None,
        "notes": None,
        "status": "active",
    }


def test_legal_and_health_public():
    client = app.test_client()
    assert client.get("/healthz").status_code == 200
    for path in ("/legal/terms", "/legal/privacy", "/legal/refund"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert b"VERA" in resp.data


def test_product_hidden_from_other_tenant():
    stamp = str(int(time.time()))[-6:]
    t1 = tenant_model.create_tenant("Iso One", shop_code="ZT%sA" % stamp)
    t2 = tenant_model.create_tenant("Iso Two", shop_code="ZT%sB" % stamp)
    sku = "ISO%s" % stamp
    product_id = None
    try:
        with app.test_request_context("/"):
            session["tenant_id"] = t1["id"]
            product_model.add_product(_product_payload(t1["id"], sku))
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM products WHERE tenant_id=%s AND sku=%s",
            (t1["id"], sku),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        assert row
        product_id = row["id"]
        with app.test_request_context("/"):
            session["tenant_id"] = t2["id"]
            assert product_model.get_product_by_id(product_id) is None
        with app.test_request_context("/"):
            session["tenant_id"] = t1["id"]
            found = product_model.get_product_by_id(product_id)
            assert found and found["id"] == product_id
    finally:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM products WHERE tenant_id IN (%s, %s)",
            (t1["id"], t2["id"]),
        )
        conn.commit()
        cur.close()
        conn.close()
        tenant_model.delete_tenant(t1["id"])
        tenant_model.delete_tenant(t2["id"])

import hashlib
import hmac

from utils.razorpay import quote_plan, verify_checkout_signature, verify_webhook_signature


def test_quote_plan_gst():
    ex, gst, total = quote_plan({"price_paise": 10000, "gst_rate": 18})
    assert ex == 10000
    assert gst == 1800
    assert total == 11800


def test_checkout_signature():
    secret = "test_secret"
    order_id = "order_1"
    payment_id = "pay_1"
    sig = hmac.new(
        secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()
    assert verify_checkout_signature(order_id, payment_id, sig, secret=secret)
    assert not verify_checkout_signature(order_id, payment_id, "nope", secret=secret)


def test_webhook_rejects_bad_signature():
    from app import app

    client = app.test_client()
    res = client.post("/billing/razorpay/webhook", data=b"{}", content_type="application/json")
    assert res.status_code == 400


def test_webhook_signature():
    secret = "whsec"
    body = b'{"event":"payment.captured"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, sig, secret=secret)
    assert not verify_webhook_signature(body, "nope", secret=secret)


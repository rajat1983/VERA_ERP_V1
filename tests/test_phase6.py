import hashlib
import hmac
from datetime import date, timedelta

from models.subscription_model import (
    evaluate_status,
    extra_seat_charge_paise,
    effective_user_limit,
    resolve_extra_user_price,
)
from utils.entitlements import feature_for_path
from utils.razorpay import verify_checkout_signature, verify_webhook_signature


def test_evaluate_status_matrix():
    today = date(2026, 11, 24)
    assert evaluate_status("pending", today, 7, today) == ("pending", False)
    assert evaluate_status("suspended", today, 7, today) == ("suspended", False)
    assert evaluate_status("active", today, 7, today) == ("active", True)
    assert evaluate_status("active", today - timedelta(days=1), 7, today) == ("grace", True)
    assert evaluate_status("active", today - timedelta(days=8), 7, today) == ("expired", False)
    assert evaluate_status("active", None, 7, today) == ("active", True)


def test_razorpay_signatures():
    secret = "test_secret"
    order_id, payment_id = "order_1", "pay_1"
    sig = hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert verify_checkout_signature(order_id, payment_id, sig, secret)
    assert not verify_checkout_signature(order_id, payment_id, "nope", secret)
    body = b'{"event":"payment.captured"}'
    wh = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, wh, secret)
    assert not verify_webhook_signature(body, "nope", secret)


def test_extra_user_seats_and_price():
    assert effective_user_limit(5, 2) == 7
    assert extra_seat_charge_paise(2, 20000) == 40000
    assert resolve_extra_user_price(None, 20000) == 20000
    assert resolve_extra_user_price(15000, 20000) == 15000
    assert resolve_extra_user_price(0, 20000) == 0


def test_pos_not_confused_with_settings():
    assert feature_for_path("/settings") is None
    assert feature_for_path("/pos") == "pos"

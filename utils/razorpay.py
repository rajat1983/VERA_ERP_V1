import base64
import hmac
import hashlib
import json
import urllib.error
import urllib.request

from models import platform_settings_model


class RazorpayError(ValueError):
    pass


def quote_plan(plan):
    ex = int(plan.get("price_paise") or 0)
    gst_rate = float(plan.get("gst_rate") or 0)
    gst = int(round(ex * gst_rate / 100.0))
    return ex, gst, ex + gst


def verify_checkout_signature(order_id, payment_id, signature, secret=None):
    secret = secret if secret is not None else platform_settings_model.get_value("razorpay_key_secret")
    payload = f"{order_id}|{payment_id}"
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def verify_webhook_signature(body, signature, secret=None):
    secret = secret if secret is not None else platform_settings_model.get_value("razorpay_webhook_secret")
    if not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def create_order(amount_paise, receipt, notes):
    key_id = platform_settings_model.get_value("razorpay_key_id").strip()
    secret = platform_settings_model.get_value("razorpay_key_secret").strip()
    if not key_id or not secret:
        raise RazorpayError("Razorpay is not configured.")
    payload = json.dumps(
        {
            "amount": int(amount_paise),
            "currency": "INR",
            "receipt": receipt[:40],
            "notes": notes,
        }
    ).encode("utf-8")
    auth = base64.b64encode(f"{key_id}:{secret}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        "https://api.razorpay.com/v1/orders",
        data=payload,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RazorpayError(f"Razorpay order failed: {detail[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RazorpayError("Could not reach Razorpay.") from exc
    if not data.get("id"):
        raise RazorpayError("Razorpay did not return an order id.")
    return data

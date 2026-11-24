import json

from flask import Blueprint, jsonify, render_template, request, session

from models import platform_billing_model, platform_settings_model, subscription_model
from utils import razorpay as razorpay_util
from utils.auth import admin_required

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


def _shop_admin():
    return (session.get("role") or "").lower() == "admin"


@billing_bp.route("/")
def home():
    tenant_id = session.get("tenant_id")
    access = subscription_model.access(tenant_id)
    plans = subscription_model.list_plans(public_only=True)
    invoices = platform_billing_model.list_for_tenant(tenant_id) if tenant_id else []
    return render_template(
        "billing/status.html",
        access=access,
        plans=plans,
        invoices=invoices,
        razorpay_ready=platform_settings_model.razorpay_configured(),
        razorpay_key=platform_settings_model.get_value("razorpay_key_id"),
        format_price=subscription_model.format_price,
        can_pay=_shop_admin(),
    )


@billing_bp.route("/expired")
def expired():
    tenant_id = session.get("tenant_id")
    access = subscription_model.access(tenant_id)
    plans = subscription_model.list_plans(public_only=True)
    return render_template(
        "billing/expired.html",
        access=access,
        plans=plans,
        razorpay_ready=platform_settings_model.razorpay_configured(),
        razorpay_key=platform_settings_model.get_value("razorpay_key_id"),
        format_price=subscription_model.format_price,
        can_pay=_shop_admin(),
    )


@billing_bp.route("/razorpay/order", methods=["POST"])
@admin_required
def create_order():
    tenant_id = session.get("tenant_id")
    data = request.get_json(silent=True) or {}
    plan = subscription_model.get_plan(request.form.get("plan_id") or data.get("plan_id"))
    if not plan or not plan.get("is_public") or not plan.get("is_active"):
        return jsonify({"error": "Choose a valid plan."}), 400
    _ex, _gst, total = razorpay_util.quote_plan(plan)
    if total <= 0:
        return jsonify({"error": "This plan has no payable amount."}), 400
    try:
        order = razorpay_util.create_order(
            total,
            receipt=f"t{tenant_id}-p{plan['id']}",
            notes={"tenant_id": str(tenant_id), "plan_id": str(plan["id"])},
        )
    except razorpay_util.RazorpayError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(
        {
            "order_id": order["id"],
            "amount": total,
            "currency": "INR",
            "key_id": platform_settings_model.get_value("razorpay_key_id"),
            "plan_id": plan["id"],
            "plan_name": plan["name"],
        }
    )


@billing_bp.route("/razorpay/verify", methods=["POST"])
@admin_required
def verify():
    payload = request.get_json(silent=True) or request.form
    order_id = payload.get("razorpay_order_id")
    payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")
    plan_id = payload.get("plan_id")
    if not razorpay_util.verify_checkout_signature(order_id, payment_id, signature):
        return jsonify({"error": "Payment signature is invalid."}), 400
    plan = subscription_model.get_plan(plan_id)
    if not plan:
        return jsonify({"error": "Plan not found."}), 400
    _ex, _gst, total = razorpay_util.quote_plan(plan)
    try:
        result = platform_billing_model.fulfill(
            session["tenant_id"],
            plan,
            payment_id,
            order_id,
            total,
            source="razorpay",
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "duplicate": result.get("duplicate"), "invoice_no": result.get("invoice_no")})


@billing_bp.route("/razorpay/webhook", methods=["POST"])
def webhook():
    body = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not razorpay_util.verify_webhook_signature(body, signature):
        return jsonify({"error": "invalid signature"}), 400
    try:
        event = json.loads(body.decode("utf-8"))
    except ValueError:
        return jsonify({"error": "invalid json"}), 400
    if event.get("event") not in ("payment.captured", "order.paid"):
        return jsonify({"ok": True, "ignored": True})
    entity = (event.get("payload") or {}).get("payment", {}).get("entity") or {}
    notes = entity.get("notes") or {}
    try:
        tenant_id = int(notes.get("tenant_id") or 0)
        plan_id = int(notes.get("plan_id") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "missing notes"}), 400
    plan = subscription_model.get_plan(plan_id)
    if not tenant_id or not plan:
        return jsonify({"error": "unknown shop or plan"}), 400
    try:
        platform_billing_model.fulfill(
            tenant_id,
            plan,
            entity.get("id"),
            entity.get("order_id"),
            entity.get("amount"),
            source="razorpay",
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})

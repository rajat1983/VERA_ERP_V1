from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import payment_model
from utils.audit import write_audit

payment_bp = Blueprint("payment", __name__)


@payment_bp.route("/payments")
def list_payments():
    return render_template(
        "payments/list.html",
        payments=payment_model.get_payments(),
        unpaid=payment_model.get_unpaid_sales(),
        vendor_payments=payment_model.get_vendor_payments(),
        unpaid_purchases=payment_model.get_unpaid_purchases(),
        today=date.today().isoformat(),
    )


@payment_bp.route("/payments/add", methods=["POST"])
def add_payment():
    try:
        payment_model.add_payment(
            request.form["sale_id"],
            request.form["payment_date"],
            request.form["amount"],
            request.form.get("payment_mode", "Cash"),
            request.form.get("reference_no", ""),
            request.form.get("notes", ""),
        )
        write_audit("PAYMENT", "payments", "sale", int(request.form["sale_id"]))
        flash("Customer payment recorded.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Could not record the payment.", "danger")
    return redirect(url_for("payment.list_payments"))


@payment_bp.route("/payments/vendor", methods=["POST"])
def add_vendor_payment():
    try:
        payment_model.add_vendor_payment(
            request.form["purchase_id"],
            request.form["payment_date"],
            request.form["amount"],
            request.form.get("payment_mode", "Cash"),
            request.form.get("reference_no", ""),
            request.form.get("notes", ""),
        )
        write_audit("PAYMENT", "payments", "purchase", int(request.form["purchase_id"]))
        flash("Vendor payment recorded.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Could not record the vendor payment.", "danger")
    return redirect(url_for("payment.list_payments"))

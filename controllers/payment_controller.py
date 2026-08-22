from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash

from models import payment_model

payment_bp = Blueprint("payment", __name__)


@payment_bp.route("/payments")
def list_payments():
    return render_template(
        "payments/list.html",
        payments=payment_model.get_payments(),
        unpaid=payment_model.get_unpaid_sales(),
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
        flash("Payment recorded.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("payment.list_payments"))

from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import purchase_model
from models import vendor_model
from models import product_model

purchase_bp = Blueprint("purchase", __name__)

@purchase_bp.route("/purchases")
def list_purchases():

    purchases = purchase_model.get_all_purchases()

    return render_template(
        "purchases/list.html",
        purchases=purchases
    )

@purchase_bp.route("/purchases/add", methods=["GET", "POST"])
def add_purchase():

    if request.method == "POST":

        # Generate Purchase Number
        purchase_no = purchase_model.generate_purchase_number()

        vendor_id = request.form.get("vendor_id")
        vendor_invoice_no = request.form.get("vendor_invoice_no")
        purchase_date = request.form.get("purchase_date")

        products = request.form.getlist("product_id[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")

        items = []

        for i in range(len(products)):

            if not products[i]:
                continue

            qty = qtys[i].strip()
            price = prices[i].strip()

            if not qty or not price:
                continue

            items.append({
                "product_id": int(products[i]),
                "qty": int(qty),
                "price": float(price)
            })

        if not items:
            flash("Please add at least one product.", "danger")
            return redirect(url_for("purchase.add_purchase"))

        try:

            purchase_model.create_purchase(
                purchase_no,
                vendor_id,
                vendor_invoice_no,
                purchase_date,
                items
            )

            flash("Purchase added & stock updated successfully.", "success")

            return redirect(url_for("purchase.list_purchases"))

        except Exception as e:

            flash(f"Error: {str(e)}", "danger")

            return redirect(url_for("purchase.add_purchase"))

    # -------------------------
    # GET Request
    # -------------------------

    vendors = product_model.get_vendors()
    products = product_model.get_products()

    purchase_no = purchase_model.generate_purchase_number()

    return render_template(
        "purchases/add.html",
        vendors=vendors,
        products=products,
        purchase_no=purchase_no
    )
@purchase_bp.route("/purchases/view/<int:id>")
def view_purchase(id):

    purchase, items = purchase_model.get_purchase_by_id(id)

    return render_template(
        "purchases/view.html",
        purchase=purchase,
        items=items
    )
@purchase_bp.route("/purchases/delete/<int:id>")
def delete_purchase(id):

    purchase_model.delete_purchase(id)

    flash("Purchase deleted and stock reversed successfully", "success")
    return redirect(url_for("purchase.list_purchases"))
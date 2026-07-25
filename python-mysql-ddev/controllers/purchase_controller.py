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

@purchase_bp.route("/purchases/add", methods=["GET","POST"])
def add_purchase():

    if request.method == "POST":

        vendor_id = request.form.get("vendor_id")
        invoice_no = request.form.get("invoice_no")
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
                "product_id": products[i],
                "qty": int(qty),
                "price": float(price)
            })

        if not items:
            flash("Please add at least one product", "danger")
            return redirect(url_for("purchase.add_purchase"))

        purchase_model.create_purchase(
            vendor_id,
            invoice_no,
            purchase_date,
            items
        )

        flash("Purchase added & stock updated successfully", "success")
        return redirect(url_for("purchase.list_purchases"))

    #vendors = vendor_model.get_all_vendors(search, limit, offset)
    vendors = product_model.get_vendors()
    products = product_model.get_products()

    return render_template(
        "purchases/add.html",
        vendors=vendors,
        products=products
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
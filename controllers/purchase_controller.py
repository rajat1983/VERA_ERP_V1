from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import purchase_model
from models import vendor_model
from models import product_model
from models.purchase_cancel import cancel_purchase
from utils.audit import write_audit


purchase_bp = Blueprint("purchase", __name__)

@purchase_bp.route("/purchases")
def list_purchases():

    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")
    per_page = 10
    offset = (page - 1) * per_page

    purchases = purchase_model.get_all_purchases(search, per_page, offset)
    total = purchase_model.get_purchase_count(search)
    total_pages = (total + per_page - 1) // per_page if total else 1

    return render_template(
        "purchases/list.html",
        purchases=purchases,
        page=page,
        total_pages=total_pages,
        q=search
    )

@purchase_bp.route("/purchases/add", methods=["GET", "POST"])
def add_purchase():

    vendors = product_model.get_vendors()
    products = product_model.get_products()

    purchase_no = purchase_model.generate_purchase_number()

    from datetime import date
    today = date.today().isoformat()
    if request.method == "POST":

        vendor_id = request.form.get("vendor_id")
        vendor_invoice_no = request.form.get("vendor_invoice_no")
        purchase_date = request.form.get("purchase_date")

        # -----------------------------------------
        # Duplicate Vendor Invoice Validation
        # -----------------------------------------

        if purchase_model.purchase_invoice_exists(
            vendor_id,
            vendor_invoice_no
        ):

            flash(
                "This Vendor Invoice Number already exists.",
                "danger"
            )

            return render_template(
                "purchases/add.html",
                vendors=vendors,
                products=products,
                purchase_no=purchase_no
                
            )

        products_list = request.form.getlist("product_id[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")

        items = []

        for i in range(len(products_list)):

            if not products_list[i]:
                continue

            qty = qtys[i].strip()
            price = prices[i].strip()

            if not qty or not price:
                continue

            items.append({
                "product_id": int(products_list[i]),
                "qty": int(qty),
                "price": float(price)
            })

        # -----------------------------------------
        # At Least One Product
        # -----------------------------------------

        if not items:

            flash(
                "Please add at least one product.",
                "danger"
            )

            return render_template(
                "purchases/add.html",
                vendors=vendors,
                products=products,
                purchase_no=purchase_no
            )

        try:

            purchase_model.create_purchase(
                purchase_no,
                vendor_id,
                vendor_invoice_no,
                purchase_date,
                items,
                discount=request.form.get("discount", 0)
            )

            flash(
                "Purchase added & stock updated successfully.",
                "success"
            )

            return redirect(
                url_for("purchase.list_purchases")
            )

        except Exception as e:

            flash(
                f"Error : {str(e)}",
                "danger"
            )

            return render_template(
                "purchases/add.html",
                vendors=vendors,
                products=products,
                purchase_no=purchase_no
            )

    return render_template(
        "purchases/add.html",
        vendors=vendors,
        products=products,
        purchase_no=purchase_no,
        today=today
    )
@purchase_bp.route("/purchases/view/<int:id>")
def view_purchase(id):

    purchase, items = purchase_model.get_purchase_by_id(id)

    return render_template(
        "purchases/view.html",
        purchase=purchase,
        items=items
    )
@purchase_bp.route("/purchases/delete/<int:id>", methods=["POST"])
def delete_purchase(id):

    try:
        cancel_purchase(id)
        write_audit("CANCEL", "purchase", "purchase", id)
        flash("Purchase cancelled and stock reversed successfully", "warning")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Could not cancel this purchase.", "danger")
    return redirect(url_for("purchase.list_purchases"))

@purchase_bp.route("/purchases/cancel/<int:id>", methods=["POST"])
def cancel_purchase_route(id):

    try:
        cancel_purchase(id)
        write_audit("CANCEL", "purchase", "purchase", id)
        flash("Purchase cancelled and stock reversed successfully", "warning")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception:
        flash("Could not cancel this purchase.", "danger")
    return redirect(url_for("purchase.list_purchases"))

@purchase_bp.route("/purchases/edit/<int:id>", methods=["GET", "POST"])
@purchase_bp.route("/purchases/edit/<int:id>", methods=["GET", "POST"])
def edit_purchase(id):

    vendors = product_model.get_vendors()
    products = product_model.get_products()

    purchase, purchase_items = purchase_model.get_purchase_by_id(id)

    if request.method == "POST":

        vendor_id = request.form.get("vendor_id")
        vendor_invoice_no = request.form.get("vendor_invoice_no")
        purchase_date = request.form.get("purchase_date")

        # -----------------------------------------
        # Duplicate Vendor Invoice Validation
        # -----------------------------------------

        if purchase_model.purchase_invoice_exists(
            vendor_id,
            vendor_invoice_no,
            exclude_purchase_id=id
        ):

            flash(
                "This Vendor Invoice Number already exists.",
                "danger"
            )

            return render_template(
                "purchases/edit.html",
                purchase=purchase,
                items=purchase_items,
                vendors=vendors,
                products=products
            )

        # -----------------------------------------
        # Read Purchase Items
        # -----------------------------------------

        products_list = request.form.getlist("product_id[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")

        items = []

        for i in range(len(products_list)):

            if not products_list[i]:
                continue

            qty = qtys[i].strip()
            price = prices[i].strip()

            if not qty or not price:
                continue

            items.append({

                "product_id": int(products_list[i]),
                "qty": int(qty),
                "price": float(price)

            })

        # -----------------------------------------
        # Validation
        # -----------------------------------------

        if not items:

            flash(
                "Please add at least one product.",
                "danger"
            )

            return render_template(
                "purchases/edit.html",
                purchase=purchase,
                items=purchase_items,
                vendors=vendors,
                products=products
            )

        try:

            purchase_model.update_purchase(

                purchase_id=id,
                vendor_id=vendor_id,
                vendor_invoice_no=vendor_invoice_no,
                purchase_date=purchase_date,
                items=items,
                discount=request.form.get("discount", 0)

            )

            flash(
                "Purchase updated successfully.",
                "success"
            )

            return redirect(
                url_for("purchase.list_purchases")
            )

        except Exception as e:

            flash(
                f"Error : {str(e)}",
                "danger"
            )

            return render_template(
                "purchases/edit.html",
                purchase=purchase,
                items=purchase_items,
                vendors=vendors,
                products=products
            )

    return render_template(
        "purchases/edit.html",
        purchase=purchase,
        items=purchase_items,
        vendors=vendors,
        products=products
    )

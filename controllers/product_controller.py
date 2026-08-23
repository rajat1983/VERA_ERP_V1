from flask import  Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models import product_model, vendor_model
import os
from werkzeug.utils import secure_filename

product_bp = Blueprint("product", __name__)
@product_bp.route("/products")
def index():
    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")
    per_page = 10
    offset = (page - 1) * per_page

    #total_products = len(products)
   # total_units = sum([p["stock_qty"] for p in products])
    products = product_model.get_all_products(search, per_page, offset)
    total = product_model.get_product_count(search)
    total_pages = (total + per_page - 1) // per_page


    return render_template(
    "products/list.html",
    products=products,
    page=page,
    total_pages=total_pages,
    total=total,
    q=search
)


@product_bp.route("/products/add", methods=["GET", "POST"])
def add_product():

    vendors = product_model.get_vendors()
    product_code = product_model.generate_product_code()

    if request.method == "POST":

        try:

            # -----------------------------
            # Upload Image
            # -----------------------------
            image_name = None
            image = request.files.get("image")

            if image and image.filename:

                image_name = secure_filename(image.filename)

                upload_path = os.path.join(
                    current_app.static_folder,
                    "uploads",
                    "products"
                )

                os.makedirs(upload_path, exist_ok=True)

                image.save(
                    os.path.join(upload_path, image_name)
                )

            # -----------------------------
            # Prepare Data
            # -----------------------------
            data = {
                "vendor_id": request.form.get("vendor_id"),
                "name": request.form.get("name"),
                "sku": request.form.get("sku"),
                "image": image_name,
                "cost_price": request.form.get("cost_price"),
                "selling_price": request.form.get("selling_price"),
                "stock_qty": request.form.get("stock_qty"),
                "reorder_level": request.form.get("reorder_level"),
                "tax_rate": request.form.get("tax_rate") or 0,
                "hsn_code": request.form.get("hsn_code"),
                "unit": request.form.get("unit") or "pcs",
                "product_type": request.form.get("product_type") or "finished_goods",
                "status": request.form.get("status")
            }

            # -----------------------------
            # Duplicate Validation
            # -----------------------------
            if product_model.product_name_exists(data["name"]):

                flash("Product name already exists.", "danger")

                return render_template(
                    "products/add.html",
                    vendors=vendors,
                    product_code=product_code
                )

            # -----------------------------
            # Save Product
            # -----------------------------
            product_model.add_product(data)

            flash("Product Added Successfully.", "success")

            return redirect(url_for("product.index"))

        except Exception as e:

            print("Product Add Error :", e)

            flash(f"Error : {e}", "danger")

            return render_template(
                "products/add.html",
                vendors=vendors,
                product_code=product_code
            )

    # GET Request
    return render_template(
        "products/add.html",
        vendors=vendors,
        product_code=product_code
    )

@product_bp.route("/products/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    product = product_model.get_product_by_id(id)
    vendors = product_model.get_vendors()

    if request.method == "POST":

        # Keep existing image
        image_name = product["image"]

        image = request.files.get("image")

        if image and image.filename:

            image_name = secure_filename(image.filename)

            upload_path = os.path.join(
                current_app.static_folder,
                "uploads",
                "products"
            )

            os.makedirs(upload_path, exist_ok=True)

            image.save(
                os.path.join(upload_path, image_name)
            )

        data = {

            "vendor_id": request.form["vendor_id"],
            "name": request.form["name"],
            "sku": request.form["sku"],
            "image": image_name,
            "cost_price": request.form["cost_price"],
            "selling_price": request.form["selling_price"],
            "stock_qty": request.form["stock_qty"],
            "reorder_level": request.form["reorder_level"],
            "tax_rate": request.form.get("tax_rate") or 0,
            "hsn_code": request.form.get("hsn_code"),
            "unit": request.form.get("unit") or "pcs",
            "product_type": request.form.get("product_type") or "finished_goods",
            "status": request.form["status"]

        }

        # Duplicate Product Name Validation
        if product_model.product_name_exists(data["name"], id):

            flash("Product name already exists.", "danger")

            return render_template(
                "products/edit.html",
                product=product,
                vendors=vendors
            )

        product_model.update_product(id, data)

        flash("Product Updated Successfully.", "success")

        return redirect(url_for("product.index"))

    return render_template(
        "products/edit.html",
        product=product,
        vendors=vendors
    )

@product_bp.route("/products/delete/<int:id>")
def delete(id):

    can_delete, message = product_model.can_delete_product(id)

    if not can_delete:
        flash(message, "danger")
        return redirect(url_for("product.index"))

    product_model.delete_product(id)

    flash("Product deleted successfully.", "success")

    return redirect(url_for("product.index"))

@product_bp.route("/product-search")
def product_search():
    q = request.args.get("q", "")
    products = product_model.product_search(q)
    return jsonify(products)

def _safe_return_path(value, default="/products"):
    if not value or not isinstance(value, str):
        return default
    if not value.startswith("/") or value.startswith("//") or ":" in value:
        return default
    return value


@product_bp.route("/products/view/<int:id>")
def view_product(id):

    product = product_model.get_product_by_id(id)

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("product.index"))

    back_href = _safe_return_path(request.args.get("next"), "/products")
    if back_href.startswith("/stock-movements"):
        back_label = "Back to movements"
    elif back_href.startswith("/stock"):
        back_label = "Back to stock"
    else:
        back_label = "Back to products"

    return render_template(
        "products/view.html",
        product=product,
        back_href=back_href,
        back_label=back_label,
    )
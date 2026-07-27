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
        q=search
    )


@product_bp.route("/products/add", methods=["GET", "POST"])
def add_product():

    vendors = product_model.get_vendors()
    product_code = product_model.generate_product_code()

    if request.method == "POST":

        image_name = None

        image = request.files.get("image")

        if image and image.filename:

            image_name = secure_filename(image.filename)

            image.save(
                os.path.join(
                    "static/uploads/products",
                    image_name
                )
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
            "status": request.form["status"]

        }

        product_model.add_product(data)

        flash("Product Added", "success")

        return redirect(url_for("product.index"))

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

        # Keep existing image by default
        image_name = product["image"]

        # Check if a new image is uploaded
        image = request.files.get("image")

        if image and image.filename:

            image_name = secure_filename(image.filename)

            upload_path = os.path.join(
                current_app.static_folder,
                "uploads",
                "products"
            )

            # Create folder if it doesn't exist
            os.makedirs(upload_path, exist_ok=True)

            image.save(
                os.path.join(upload_path, image_name)
            )

        data = {

            "vendor_id": request.form["vendor_id"],
            "name": request.form["name"],

            # Keep existing Product Code
            "sku": request.form["sku"],

            # Updated Image
            "image": image_name,

            "cost_price": request.form["cost_price"],
            "selling_price": request.form["selling_price"],
            "stock_qty": request.form["stock_qty"],
            "reorder_level": request.form["reorder_level"],
            "status": request.form["status"]

        }

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

@product_bp.route("/products/view/<int:id>")
def view_product(id):

    product = product_model.get_product_by_id(id)

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("product.index"))

    return render_template(
        "products/view.html",
        product=product
    )
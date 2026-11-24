from flask import  Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort, session
from models import product_model, vendor_model
from utils.uploads import save_product_image

product_bp = Blueprint("product", __name__)


def _product_form_data(image_name):
    return {
        "vendor_id": request.form.get("vendor_id"),
        "name": request.form.get("name"),
        "short_name": request.form.get("short_name"),
        "brand": request.form.get("brand"),
        "sku": request.form.get("sku"),
        "barcode": request.form.get("barcode"),
        "image": image_name,
        "cost_price": request.form.get("cost_price"),
        "selling_price": request.form.get("selling_price"),
        "mrp": request.form.get("mrp"),
        "stock_qty": request.form.get("stock_qty"),
        "reorder_level": request.form.get("reorder_level"),
        "low_stock_threshold": request.form.get("low_stock_threshold") or 0,
        "tax_rate": request.form.get("tax_rate") or 0,
        "hsn_code": request.form.get("hsn_code"),
        "unit": request.form.get("unit") or "pcs",
        "product_type": request.form.get("product_type") or "finished_goods",
        "category": request.form.get("category"),
        "description": request.form.get("description"),
        "notes": request.form.get("notes"),
        "status": request.form.get("status"),
    }
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
            image_name = save_product_image(request.files.get("image"), session.get("tenant_id"))

            # -----------------------------
            # Prepare Data
            # -----------------------------
            data = _product_form_data(image_name)

            # -----------------------------
            # Duplicate Validation
            # -----------------------------
            if product_model.product_name_exists(data["name"]):

                flash("Product name already exists.", "danger")

                return render_template(
                    "products/add.html",
                    vendors=vendors,
                    product_code=product_code,
                    units=product_model.UNITS,
                )

            # -----------------------------
            # Save Product
            # -----------------------------
            product_model.add_product(data)

            flash("Product Added Successfully.", "success")

            if request.form.get("action") == "another":
                return redirect(url_for("product.add_product"))

            return redirect(url_for("product.index"))

        except Exception as e:

            print("Product Add Error :", e)

            flash(f"Error : {e}", "danger")

            return render_template(
                "products/add.html",
                vendors=vendors,
                product_code=product_code,
                units=product_model.UNITS,
            )

    # GET Request
    return render_template(
        "products/add.html",
        vendors=vendors,
        product_code=product_code,
        units=product_model.UNITS,
    )

@product_bp.route("/products/edit/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    product = product_model.get_product_by_id(id)
    vendors = product_model.get_vendors()

    if not product:
        abort(404)

    if request.method == "POST":

        # Keep existing image
        image_name = product["image"]

        image = request.files.get("image")
        if image and image.filename:
            image_name = save_product_image(image, session.get("tenant_id"))

        data = _product_form_data(image_name)

        # Duplicate Product Name Validation
        if product_model.product_name_exists(data["name"], id):

            flash("Product name already exists.", "danger")

            return render_template(
                "products/edit.html",
                product=product,
                vendors=vendors,
                units=product_model.UNITS,
            )

        product_model.update_product(id, data)

        flash("Product Updated Successfully.", "success")

        return redirect(url_for("product.index"))

    return render_template(
        "products/edit.html",
        product=product,
        vendors=vendors,
        units=product_model.UNITS,
    )


@product_bp.route("/products/categories")
def categories():
    q = request.args.get("q", "")
    return jsonify(product_model.search_categories(q))


@product_bp.route("/products/categories/quick-add", methods=["POST"])
def quick_add_category():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    try:
        row = product_model.add_category(name)
    except ValueError as ex:
        return jsonify(ok=False, error=str(ex)), 400
    return jsonify(ok=True, id=row["id"], name=row["name"])

@product_bp.route("/products/delete/<int:id>", methods=["POST"])
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
        abort(404)

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
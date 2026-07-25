from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import product_model, vendor_model

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
    if request.method == "POST":
        data = {
            "vendor_id" : request.form["vendor_id"],
            "name": request.form["name"],
            "sku": request.form["sku"],
            "cost_price": request.form["cost_price"],
            "selling_price": request.form["selling_price"],
            "stock_qty": request.form["stock_qty"],
            "reorder_level": request.form["reorder_level"],
            "status": request.form["status"]
        }
        product_model.add_product(data)
        flash("Product Added", "success")
        return redirect(url_for("product.index"))   
    
    return render_template("products/add.html",vendors=vendors)

@product_bp.route("/products/edit/<int:id>", methods=["GET", "POST"])

def edit_product(id):
    product = product_model.get_product_by_id(id)
    #vendors = vendor_model.get_all_vendors()
    vendors = product_model.get_vendors()
   
    if request.method == "POST":
        data = {
            "vendor_id" : request.form["vendor_id"],
            "name": request.form["name"],
            "sku": request.form["sku"],
            "cost_price": request.form["cost_price"],
            "selling_price": request.form["selling_price"],
            "stock_qty": request.form["stock_qty"],
            "reorder_level": request.form["reorder_level"],
            "status": request.form["status"]
        }
        product_model.update_product(id, data)
        
        flash("Product Updated", "success")
        return redirect(url_for("product.index"))

    return render_template("products/edit.html", product=product,vendors=vendors)

@product_bp.route("/products/delete/<int:id>")
def delete(id):
    product_model.delete_product(id)
    flash("Product Deleted", "warning")
    return redirect(url_for("product.index"))

@product_bp.route("/product-search")
def product_search():
    q = request.args.get("q", "")
    products = product_model.product_search(q)
    return jsonify(products)

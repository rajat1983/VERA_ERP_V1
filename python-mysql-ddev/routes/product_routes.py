from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import product_model

product_bp = Blueprint("product", __name__)


@product_bp.route("/products")
def index():
    products = product_model.get_all_products()
    return render_template("products/list.html", products=products)


@product_bp.route("/products/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form["name"]
        sku = request.form["sku"]
        price = request.form["price"]
        stock = request.form["stock"]

        product_model.add_product(name, sku, price, stock)

        flash("Product added successfully", "success")
        return redirect(url_for("product.index"))

    return render_template("products/add.html")


@product_bp.route("/products/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    product = product_model.get_product(id)

    if request.method == "POST":
        name = request.form["name"]
        sku = request.form["sku"]
        price = request.form["price"]
        stock = request.form["stock"]

        product_model.update_product(id, name, sku, price, stock)

        flash("Product updated", "success")
        return redirect(url_for("product.index"))

    return render_template("products/edit.html", product=product)


@product_bp.route("/products/delete/<int:id>")
def delete(id):
    product_model.delete_product(id)
    flash("Product deleted", "danger")
    return redirect(url_for("product.index"))

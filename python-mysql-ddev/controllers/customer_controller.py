from flask import Blueprint, render_template, redirect, request, flash, url_for, jsonify
from models import customer_model
import math

customer_bp = Blueprint("customer", __name__)
@customer_bp.route("/customers")
def index():
    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")
    per_page = 10
    offset = (page - 1) * per_page

    customers = customer_model.get_all_customers(search, per_page, offset)
    total = customer_model.get_customer_count(search)
    total_pages = math.ceil(total / per_page)

    return render_template(
        "/customer/list.html",  
        customers=customers,
        page=page,
        total_pages=total_pages,
        q=search
    )

@customer_bp.route("/customer/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        status = request.form["status"].strip()

        if not name:
            flash("Name is required", "danger")
            return redirect(url_for("customer.add"))

        customer_model.add_customer(name, email, phone,address,status)
        flash("Customer added successfully", "success")
        return redirect(url_for("customer.index"))

    return render_template("customer/add.html")


@customer_bp.route("/customer/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    customer = customer_model.get_customer_by_id(id)

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        status = request.form["status"].strip()

        customer_model.update_customer(id, name, email, phone,address,status)

        flash("Customer updated successfully", "success")
        return redirect(url_for("customer.index"))

    return render_template("/customer/edit.html", customer=customer)


@customer_bp.route("/customer/delete/<int:id>")
def delete(id):
    customer_model.delete_customer(id)
    flash("Customer deleted", "warning")
    return redirect(url_for("customer.index"))


@customer_bp.route("/customer/auto-search")
def auto_search():
    q = request.args.get("q", "")
    data = customer_model.search_customers(q)
    return jsonify(data)

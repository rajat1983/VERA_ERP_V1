from flask import Blueprint, render_template, redirect, request, flash, url_for, jsonify, abort
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

    customer_code = customer_model.generate_customer_code()

    if request.method == "POST":

        # ----------------------------
        # Read Form
        # ----------------------------

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        status = request.form["status"].strip()

        gst_no = request.form.get("gst_no", "").strip().upper()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()

        # ----------------------------
        # Validation
        # ----------------------------

        if not name:

            flash(
                "Customer Name is required.",
                "danger"
            )

            return render_template(
                "customer/add.html",
                customer_code=customer_code
            )

        # ----------------------------
        # Duplicate Validation
        # ----------------------------

        email_exists, phone_exists = customer_model.check_duplicate_customer(
            email,
            phone
        )

        if email_exists and phone_exists:

            flash(
                "Email and Mobile Number already exist.",
                "danger"
            )

            return render_template(
                "customer/add.html",
                customer_code=customer_code
            )

        elif email_exists:

            flash(
                "Email already exists.",
                "danger"
            )

            return render_template(
                "customer/add.html",
                customer_code=customer_code
            )

        elif phone_exists:

            flash(
                "Mobile Number already exists.",
                "danger"
            )

            return render_template(
                "customer/add.html",
                customer_code=customer_code
            )

        # ----------------------------
        # Save Customer
        # ----------------------------

        customer_model.add_customer(

            customer_code,
            name,
            email,
            phone,
            gst_no,
            address,
            city,
            state,
            pincode,
            status

        )

        flash(
            "Customer added successfully.",
            "success"
        )

        return redirect(
            url_for("customer.index")
        )

    # ----------------------------
    # GET
    # ----------------------------

    return render_template(
        "customer/add.html",
        customer_code=customer_code
    )

@customer_bp.route("/customer/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    customer = customer_model.get_customer_by_id(id)
    if not customer:
        abort(404)

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        status = request.form["status"].strip()

        gst_no = request.form.get("gst_no", "").strip().upper()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()

        # -----------------------------------------
        # Validation
        # -----------------------------------------

        if not name:

            flash(
                "Customer Name is required.",
                "danger"
            )

            return render_template(
                "customer/edit.html",
                customer=customer
            )

        # -----------------------------------------
        # Duplicate Validation
        # -----------------------------------------

        email_exists, phone_exists = customer_model.check_duplicate_customer(
            email,
            phone,
            exclude_id=id
        )

        if email_exists and phone_exists:

            flash(
                "Email and Mobile Number already exist.",
                "danger"
            )

            return render_template(
                "customer/edit.html",
                customer=customer
            )

        elif email_exists:

            flash(
                "Email already exists.",
                "danger"
            )

            return render_template(
                "customer/edit.html",
                customer=customer
            )

        elif phone_exists:

            flash(
                "Mobile Number already exists.",
                "danger"
            )

            return render_template(
                "customer/edit.html",
                customer=customer
            )

        # -----------------------------------------
        # Update Customer
        # -----------------------------------------

        customer_model.update_customer(
            id,
            name,
            email,
            phone,
            gst_no,
            address,
            city,
            state,
            pincode,
            status
        )

        flash(
            "Customer updated successfully.",
            "success"
        )

        return redirect(
            url_for("customer.index")
        )

    return render_template(
        "customer/edit.html",
        customer=customer
    )


@customer_bp.route("/customer/delete/<int:id>", methods=["POST"])
def delete(id):
    can_delete, message = customer_model.can_delete_customer(id)
    if not can_delete:
        flash(message, "danger")
        return redirect(url_for("customer.index"))
    customer_model.delete_customer(id)
    flash("Customer deleted", "warning")
    return redirect(url_for("customer.index"))


@customer_bp.route("/customer/auto-search")
def auto_search():
    q = request.args.get("q", "")
    data = customer_model.search_customers(q)
    return jsonify(data)
# ==========================================
# View Customer
# ==========================================

@customer_bp.route("/customer/view/<int:id>")
def view(id):

    customer = customer_model.get_customer_by_id(id)

    if not customer:
        abort(404)

    return render_template(
        "customer/view.html",
        customer=customer
    )
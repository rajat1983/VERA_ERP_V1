from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import vendor_model
from utils.mailer import send_email, ADMIN_EMAIL
vendor_bp = Blueprint("vendor", __name__)
@vendor_bp.route("/vendors")
def list_vendors():

    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")

    per_page = 10
    offset = (page - 1) * per_page

    vendors = vendor_model.get_all_vendors(
        search,
        per_page,
        offset
    )

    total_records = vendor_model.get_vendor_count(search)

    total_pages = (
        total_records + per_page - 1
    ) // per_page

    return render_template(

        "vendor/list.html",

        vendors=vendors,

        page=page,

        per_page=per_page,

        total_pages=total_pages,

        total_records=total_records

    )
       

@vendor_bp.route("/vendors/add", methods=["GET", "POST"])
def add_vendor():

    vendor_code = vendor_model.generate_vendor_code()

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        gst_number = request.form.get("gst_number", "").strip().upper()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        status = request.form.get("status", "active").strip().lower()

        # -----------------------------------------
        # Required Field Validation
        # -----------------------------------------

        if not name:

            flash(
                "Vendor Name is required.",
                "danger"
            )

            return render_template(
                "vendor/add.html",
                vendor_code=vendor_code
            )

        if not phone:

            flash(
                "Mobile Number is required.",
                "danger"
            )

            return render_template(
                "vendor/add.html",
                vendor_code=vendor_code
            )

        # -----------------------------------------
        # Mobile Validation
        # -----------------------------------------

        if not phone.isdigit() or len(phone) != 10:

            flash(
                "Mobile Number must contain exactly 10 digits.",
                "danger"
            )

            return render_template(
                "vendor/add.html",
                vendor_code=vendor_code
            )

        # -----------------------------------------
        # Email Validation
        # -----------------------------------------

        if email:

            import re

            pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'

            if not re.match(pattern, email):

                flash(
                    "Please enter a valid Email Address.",
                    "danger"
                )

                return render_template(
                    "vendor/add.html",
                    vendor_code=vendor_code
                )

        # -----------------------------------------
        # GST Validation
        # -----------------------------------------

        if gst_number:

            if len(gst_number) != 15:

                flash(
                    "GST Number must be exactly 15 characters.",
                    "danger"
                )

                return render_template(
                    "vendor/add.html",
                    vendor_code=vendor_code
                )

        # -----------------------------------------
        # PIN Code Validation
        # -----------------------------------------

        if pincode:

            if not pincode.isdigit() or len(pincode) != 6:

                flash(
                    "PIN Code must contain exactly 6 digits.",
                    "danger"
                )

                return render_template(
                    "vendor/add.html",
                    vendor_code=vendor_code
                )

        # -----------------------------------------
        # Duplicate Validation
        # -----------------------------------------

        email_exists, phone_exists, gst_exists = vendor_model.check_duplicate_vendor(
            email,
            phone,
            gst_number
        )

        if email_exists:

            flash(
                "Email already exists.",
                "danger"
            )

            return render_template(
                "vendor/add.html",
                vendor_code=vendor_code
            )

        if phone_exists:

            flash(
                "Mobile Number already exists.",
                "danger"
            )

            return render_template(
                "vendor/add.html",
                vendor_code=vendor_code
            )

        if gst_exists:

            flash(
                "GST Number already exists.",
                "danger"
            )

            return render_template(
                "vendor/add.html",
                vendor_code=vendor_code
            )

        # -----------------------------------------
        # Save Vendor
        # -----------------------------------------

        vendor_model.add_vendor(

            vendor_code,
            name,
            email,
            phone,
            gst_number,
            address,
            city,
            state,
            pincode,
            status

        )

        flash(
            "Vendor added successfully.",
            "success"
        )

        return redirect(
            url_for("vendor.list_vendors")
        )

    return render_template(
        "vendor/add.html",
        vendor_code=vendor_code
    )
    

@vendor_bp.route("/vendors/edit/<int:id>", methods=["GET", "POST"])
def edit_vendor(id):

    vendor = vendor_model.get_vendor(id)

    if not vendor:

        flash(
            "Vendor not found.",
            "danger"
        )

        return redirect(
            url_for("vendor.list_vendors")
        )

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        gst_number = request.form.get("gst_number", "").strip().upper()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        status = request.form["status"].strip()

        # -----------------------------------------
        # Validation
        # -----------------------------------------

        if not name:

            flash(
                "Vendor Name is required.",
                "danger"
            )

            return render_template(
                "vendor/edit.html",
                vendor=vendor
            )

        # -----------------------------------------
        # Duplicate Validation
        # -----------------------------------------

        email_exists, phone_exists, gst_exists = vendor_model.check_duplicate_vendor(

            email,
            phone,
            gst_number,
            exclude_id=id

        )

        if email_exists:

            flash(
                "Email already exists.",
                "danger"
            )

            return render_template(
                "vendor/edit.html",
                vendor=vendor
            )

        if phone_exists:

            flash(
                "Mobile Number already exists.",
                "danger"
            )

            return render_template(
                "vendor/edit.html",
                vendor=vendor
            )

        if gst_exists:

            flash(
                "GST Number already exists.",
                "danger"
            )

            return render_template(
                "vendor/edit.html",
                vendor=vendor
            )

        # -----------------------------------------
        # Update Vendor
        # -----------------------------------------

        vendor_model.update_vendor(

            id,
            name,
            email,
            phone,
            gst_number,
            address,
            city,
            state,
            pincode,
            status

        )

        flash(
            "Vendor updated successfully.",
            "success"
        )

        return redirect(
            url_for("vendor.list_vendors")
        )

    return render_template(
        "vendor/edit.html",
        vendor=vendor
    )


@vendor_bp.route("/vendors/delete/<int:id>")
def delete_vendor(id):
    vendor_model.delete_vendor(id)
    flash("Vendor deleted", "warning")
    return redirect(url_for("vendor.list_vendors"))

@vendor_bp.route("/vendor-search")
def vendor_search():
    q = request.args.get("q", "")
    vendors = vendor_model.vendor_search(q)
    return jsonify(vendors)
#AutoComplete & Add new 

@vendor_bp.route("/api/vendors/search")
def api_search_vendors():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    return jsonify(vendor_model.search_vendors(q))
   
#@vendor_bp.route("/api/vendors/add/", methods=["POST"])
@vendor_bp.route("/api/vendors/add", methods=["POST"], strict_slashes=False)
def api_add_vendor():
    data = request.get_json()

    if not data or not data.get("name"):
        return jsonify({"error": "Vendor name required"}), 400

    name = data["name"].strip()
    vendor_id = vendor_model.create_vendor(name)
    html = render_template("emails/vendor_created.html", name=name)
    # Send to Vendor (if email exists)
    # if email:
    #     send_email(email, "Vendor Created", html)
        # Send to Admin
   # send_email(ADMIN_EMAIL, "New Vendor Created", html)
    return jsonify({
        "id": vendor_id,
        "name": name
    })
    
@vendor_bp.route("/vendors/view/<int:id>")
def view_vendor(id):

    vendor = vendor_model.get_vendor_by_id(id)

    if not vendor:

        flash(
            "Vendor not found.",
            "danger"
        )

        return redirect(
            url_for("vendor.list_vendors")
        )

    return render_template(
        "vendor/view.html",
        vendor=vendor
    )




from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import vendor_model
from utils.mailer import send_email, ADMIN_EMAIL
vendor_bp = Blueprint("vendor", __name__)
@vendor_bp.route("/vendors")
def list_vendors():
    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")
    per_page = 4
    offset = (page - 1) * per_page

    vendors = vendor_model.get_all_vendors(search, per_page, offset)
    total = vendor_model.get_vendor_count(search)
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "/vendor/vendor_list.html",
        vendors=vendors,
        page=page,
        total_pages=total_pages,
        q=search
    )

@vendor_bp.route("/vendors/add", methods=["GET", "POST"])
def add_vendor():
    if request.method == "POST":
        vendor_model.add_vendor(
            request.form["name"],
            request.form["email"],
            request.form["phone"],
            request.form["address"],
            request.form["gst_number"],
            request.form["status"]
        )
        flash("Vendor added successfully", "success")
        return redirect(url_for("vendor.list_vendors"))

    return render_template("vendor/vendor_form.html", action="Add")
    

@vendor_bp.route("/vendors/edit/<int:id>", methods=["GET", "POST"])
def edit_vendor(id):
    vendor = vendor_model.get_vendor(id)

    if request.method == "POST":
        vendor_model.update_vendor(
            id,
            request.form["name"],
            request.form["email"],
            request.form["phone"],
            request.form["address"],
            request.form["gst_number"],
            request.form["status"]
        )
        flash("Vendor updated successfully", "success")
        return redirect(url_for("vendor.list_vendors"))

    return render_template("vendor/vendor_form.html", vendor=vendor, action="Edit")


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





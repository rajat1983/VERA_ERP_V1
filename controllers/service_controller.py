import math

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from models import service_model
from utils.audit import write_audit

service_bp = Blueprint("services", __name__)


def _form_values():
    try:
        price = request.form.get("price", "")
        price = float(price) if str(price).strip() != "" else 0
    except (TypeError, ValueError):
        price = 0
    return {
        "name": request.form.get("name", "").strip(),
        "category": request.form.get("category", "").strip(),
        "unit": request.form.get("unit", "").strip(),
        "price": price,
        "is_active": request.form.get("is_active") == "1",
    }


def _validate(values, exclude_id=None):
    if not values["name"]:
        return "Name is required."
    if values["unit"] not in service_model.UNITS:
        return "Select a unit."
    if values["price"] < 0:
        return "Default price cannot be negative."
    if service_model.name_exists(values["name"], exclude_id=exclude_id):
        return "A service with this name already exists."
    return None


@service_bp.route("/services/categories")
def categories():
    q = request.args.get("q", "")
    return jsonify(service_model.search_categories(q))


@service_bp.route("/services/categories/quick-add", methods=["POST"])
def quick_add_category():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    try:
        row = service_model.add_category(name)
    except ValueError as ex:
        return jsonify(ok=False, error=str(ex)), 400
    write_audit("CREATE", "services", "category", row["id"], row["name"])
    return jsonify(ok=True, id=row["id"], name=row["name"])


@service_bp.route("/services")
def index():
    page = int(request.args.get("page", 1) or 1)
    search = request.args.get("q", "")
    per_page = 10
    offset = (page - 1) * per_page
    rows = service_model.list_services(search, per_page, offset)
    total = service_model.count_services(search)
    total_pages = math.ceil(total / per_page) if total else 1
    return render_template(
        "services/list.html",
        services=rows,
        page=page,
        total_pages=total_pages,
        total=total,
        q=search,
        per_page=per_page,
    )


@service_bp.route("/services/add", methods=["GET", "POST"])
def add():
    values = {
        "name": "",
        "category": "",
        "unit": "",
        "price": "",
        "is_active": True,
    }
    if request.method == "POST":
        values = _form_values()
        error = _validate(values)
        if error:
            flash(error, "danger")
        else:
            service_id = service_model.add_service(
                values["name"],
                values["category"],
                values["unit"],
                values["price"],
                values["is_active"],
            )
            write_audit("CREATE", "services", "service", service_id, values["name"])
            flash("Service created.", "success")
            if request.form.get("action") == "another":
                return redirect(url_for("services.add"))
            return redirect(url_for("services.index"))
    return render_template(
        "services/form.html",
        mode="create",
        service=values,
        units=service_model.UNITS,
    )


@service_bp.route("/services/<int:id>/edit", methods=["GET", "POST"])
def edit(id):
    row = service_model.get_service(id)
    if not row:
        flash("Service not found.", "danger")
        return redirect(url_for("services.index"))
    if request.method == "POST":
        values = _form_values()
        error = _validate(values, exclude_id=id)
        if error:
            flash(error, "danger")
            return render_template(
                "services/form.html",
                mode="edit",
                service=values,
                service_id=id,
                units=service_model.UNITS,
            )
        service_model.update_service(
            id,
            values["name"],
            values["category"],
            values["unit"],
            values["price"],
            values["is_active"],
        )
        write_audit("UPDATE", "services", "service", id, values["name"])
        flash("Service updated.", "success")
        return redirect(url_for("services.index"))
    return render_template(
        "services/form.html",
        mode="edit",
        service=row,
        service_id=id,
        units=service_model.UNITS,
    )


@service_bp.route("/services/<int:id>/delete", methods=["POST"])
def delete(id):
    row = service_model.get_service(id)
    service_model.delete_service(id)
    write_audit("DELETE", "services", "service", id, (row or {}).get("name"))
    flash("Service deleted.", "warning")
    return redirect(url_for("services.index"))

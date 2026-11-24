import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from models import employee_model as model


employee_bp = Blueprint("employee", __name__)

@employee_bp.route("/list")
def index():
    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")
    per_page = 5
    offset = (page - 1) * per_page

    employees = model.get_employees(search, per_page, offset)
    total = model.get_employee_count(search)
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "index.html",
        employees=employees,
        page=page,
        total_pages=total_pages,
        q=search
    )
@employee_bp.route("/add")
def add():
    return render_template("add.html")


@employee_bp.route("/create", methods=["POST"])
def create():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    # Server-side validation
    if not name or not email:
        flash("Name and Email are required", "danger")
        return redirect(url_for("employee.index"))

    if len(name) < 3:
        flash("Name must be at least 3 characters", "danger")
        return redirect(url_for("employee.index"))

    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        flash("Invalid email format", "danger")
        return redirect(url_for("employee.index"))

    model.create_employee(name, email)
    flash("Employee added successfully", "success")
    return redirect(url_for("employee.index"))

@employee_bp.route("/edit/<int:id>")
def edit(id):
    emp = model.get_employee_by_id(id)
    return render_template("edit.html", employee=emp)


@employee_bp.route("/update", methods=["POST"])
def update():
    emp_id = request.form["id"]
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email:
        flash("Name and Email are required", "danger")
        return redirect(url_for("employee.edit", id=emp_id))

    if len(name) < 3:
        flash("Name must be at least 3 characters", "danger")
        return redirect(url_for("employee.edit", id=emp_id))

    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        flash("Invalid email format", "danger")
        return redirect(url_for("employee.edit", id=emp_id))

    model.update(emp_id, name, email)
    flash("Employee updated successfully", "success")

    return redirect(url_for("employee.index"))


@employee_bp.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if not model.get_employee_by_id(id):
        abort(404)
    model.delete(id)
    
    flash("Employee deleted successfully", "success")
    return redirect(url_for("employee.index"))

@employee_bp.route("/auto-search")
def auto_search():
    q = request.args.get("q", "")
    employees = model.search_employees(q)
    return jsonify(employees)


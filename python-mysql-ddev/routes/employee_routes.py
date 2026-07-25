from flask import flash
from flask import Blueprint, render_template, request, redirect, url_for
from models import employee_model

employee_bp = Blueprint("employee", __name__)

@employee_bp.route("/")
def index():
    employees = employee_model.get_all_employees()
    return render_template("index.html", employees=employees)


@employee_bp.route("/edit/<int:id>")
def edit(id):
    emp = employee_model.get_employee_by_id(id)
    return render_template("edit.html", employee=emp)


@employee_bp.route("/update", methods=["POST"])
def update():
    emp_id = request.form["id"]
    name = request.form["name"]
    email = request.form["email"]
    if not name or not email:
        flash("Name and Email are required", "danger")
        return redirect(url_for("employee.edit", id=emp_id))

    employee_model.update_employee(emp_id, name, email)
    flash("Employee updated successfully", "success")
    return redirect(url_for("employee.index"))

@employee_bp.route("/test-flash")
def test_flash():
    flash("Flash is working", "success")
    return redirect(url_for("employee.index"))
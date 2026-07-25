from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import production_model, product_model


production_bp = Blueprint("production", __name__)


@production_bp.route("/production")
def list_production():

    batches = production_model.generate_batch_code()

    return render_template(
        "production/list.html",
        batches=batches
    )


@production_bp.route("/production/add", methods=["GET","POST"])
def add_production():

    if request.method == "POST":

        try:

            product_id = request.form["product_id"]
            quantity = int(request.form["quantity"])
            wastage = int(request.form.get("wastage", 0))
            batch_date = request.form["batch_date"]

            production_model.create_production(
                product_id,
                quantity,
                wastage,
                batch_date
            )

            flash("Production created successfully", "success")

            return redirect(url_for("production.list_production"))

        except ValueError as e:

            flash(str(e), "danger")

        except Exception as e:

            flash("Error creating production: " + str(e), "danger")

    products = product_model.get_products_by_type("finished_goods")
    

    return render_template(
        "production/add.html",
        products=products
    )
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import sales_model, product_model, customer_model
from models.sales_model import get_next_invoice_number
import traceback
from num2words import num2words
 
sales_bp = Blueprint("sales", __name__)
@sales_bp.route("/sales")
def list_sales():
    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")
    per_page = 10
    offset = (page - 1) * per_page

    sales = sales_model.get_all_sales(search, per_page, offset)
    total = sales_model.get_sale_count(search)
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "/sales/sale_list.html",
        sales=sales,
        page=page,
        total_pages=total_pages,
        q=search
    )
from flask import flash

@sales_bp.route("/sales/add", methods=["GET","POST"]) 
def add_sale():
    
    if request.method == "POST":
        try:
            invoice_no = sales_model.get_next_invoice_number()
            customer_id = request.form["customer_id"]
            sale_date = request.form["sale_date"]
            remarks = request.form.get("remarks","")
            discount = request.form.get("discount","0")

            products = request.form.getlist("product_id[]")
            qtys = request.form.getlist("qty[]")
            prices = request.form.getlist("price[]")

            items = []

            for i in range(len(products)):

                if not products[i]:
                    continue

                qty = qtys[i].strip()
                price = prices[i].strip()

                qty = int(qty) if qty else 0
                price = float(price) if price else 0.0

                items.append({
                    "product_id": products[i],
                    "qty": qty,
                    "price": price
                })

            #  CALL MODEL — MAY RAISE ERROR
            sale_id = sales_model.create_sale(
                invoice_no,
                customer_id,
                sale_date,
                remarks,
                discount,
                items
            )

            flash("Sale created successfully", "success")
            return redirect(url_for("sales.list_sales"))

        except ValueError as ex:
            #  USER ERROR (like stock insufficient)
            flash(str(ex), "danger")

    
        except Exception as ex:
            traceback.print_exc()   # Print full error in terminal
            flash("Something went wrong: " + str(ex), "danger")

        # If we reached here → reload the page with user data preserved
        customers = customer_model.get_customers()
        products = product_model.get_products()

        return render_template(
            "sales/sale_create.html",
            customers=customers,
            products=products
        )

    # GET REQUEST
    customers = customer_model.get_customers()
    products = product_model.get_products()

    return render_template(
        "sales/sale_create.html",
        customers=customers,
        products=products
    )

@sales_bp.route("/sales/view/<int:sale_id>", methods=["GET"])
def sale_view(sale_id):

    sale, items = sales_model.get_sale_by_id(sale_id)

    sale["amount_in_words"] = (
        num2words(
            sale["total_amount"],
            to="currency",
            lang="en_IN"
        ).title()
    )

    return render_template(
        "sales/sale_view.html",
        sale=sale,
        items=items
    )

@sales_bp.route("/sales/delete/<int:sale_id>")
def delete_sale(sale_id):
    sales_model.delete_sale(sale_id)
    flash("Sale deleted successfully", "success")
    return redirect(url_for("sales.list_sales"))

@sales_bp.route("/sale-search")
def sale_search():
    q = request.args.get("q", "")
    sales = sales_model.sale_search(q)
    return jsonify(sales)

@sales_bp.route("/sales/<int:id>/edit")
def sale_edit(id):
    sale, items = sales_model.get_sale_by_id(id)
   #items = sales_model.get_sale_items(id)

    customers = customer_model.get_customers()
    products = product_model.get_products()

    return render_template(
        "sales/edit.html",
        sale=sale,
        items=items,
        customers=customers,
        products=products
    )

@sales_bp.route("/sales/<int:id>/update", methods=["POST"])
def sale_update(id):

    customer_id = request.form["customer_id"]
    discount = float(request.form.get("discount", 0))

    product_ids = request.form.getlist("product_id[]")
    qtys = request.form.getlist("qty[]")
    prices = request.form.getlist("price[]")

    items = []
    total = 0

    for i in range(len(product_ids)):
        if not product_ids[i]:
            continue
        
        qty = int(qtys[i])
        price = float(prices[i])
        line_total = qty * price
        total += line_total
        
        items.append({
            "product_id": product_ids[i],
            "qty": qty,
            "price": price,
            "line_total": line_total
        })

    grand_total = total - discount

    sales_model.update_sale(id, customer_id, discount, grand_total, items)

    flash("Sale updated successfully!", "success")

    return redirect(url_for("sales.list_sales"))


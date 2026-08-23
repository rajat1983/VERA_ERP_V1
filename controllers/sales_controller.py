from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import date
from utils.audit import write_audit
from models import sales_model, product_model, customer_model
import traceback
from num2words import num2words
from models import company_model

sales_bp = Blueprint("sales", __name__)

@sales_bp.route("/sales")
def list_sales():

    page = int(
        request.args.get("page", 1)
    )

    search = request.args.get(
        "q",
        ""
    )

    per_page = 10

    offset = (
        page - 1
    ) * per_page

    # ==========================================
    # Sales List
    # ==========================================

    sales = sales_model.get_all_sales(
        search,
        per_page,
        offset
    )

    total = sales_model.get_sale_count(
        search
    )

    total_pages = (
        total + per_page - 1
    ) // per_page

    # ==========================================
    # Sales KPI Summary
    # ==========================================

    sales_summary = (
        sales_model.get_sales_summary()
    )

    # ==========================================
    # Render Sales List
    # ==========================================

    return render_template(
        "/sales/sale_list.html",
        sales=sales,
        sales_summary=sales_summary,
        page=page,
        total_pages=total_pages,
        q=search
    )

@sales_bp.route("/sales/add", methods=["GET","POST"]) 

def add_sale():
    from datetime import date

    today = date.today().isoformat()

    if request.method == "POST":

        try:

            # ==========================================
            # 1. Get Sale Information
            # ==========================================

            customer_id = request.form["customer_id"]

            sale_date = request.form["sale_date"]

            remarks = request.form.get(
                "remarks",
                ""
            )           

            # ==========================================
            # 2. Validate Discount
            # ==========================================

            discount_value = request.form.get(
                "discount",
                "0"
                ).strip()

            try:
                discount = float(
                    discount_value
                    if discount_value
                    else 0
                )
            except ValueError:
                raise ValueError(
                "Discount must be a valid percentage."
            )

            if discount < 0 or discount > 100:
                raise ValueError(
                "Discount must be between 0% and 100%."
            )

            # ==========================================
            # 3. Get Sale Items
            # ==========================================

            products = request.form.getlist(
                "product_id[]"
            )

            qtys = request.form.getlist(
                "qty[]"
            )

            prices = request.form.getlist(
                "price[]"
            )

            items = []

            # ==========================================
            # 4. Validate & Prepare Items
            # ==========================================

            for i in range(len(products)):

                if not products[i]:
                    continue

                qty_value = qtys[i].strip()
                price_value = prices[i].strip()

                qty = (
                    int(qty_value)
                    if qty_value
                    else 0
                )

                price = (
                    float(price_value)
                    if price_value
                    else 0.0
                )

                if qty <= 0:
                    raise ValueError(
                        "Quantity must be greater than zero."
                    )

                if price < 0:
                    raise ValueError(
                        "Price cannot be negative."
                    )

                items.append({
                    "product_id": products[i],
                    "qty": qty,
                    "price": price
                })

            # ==========================================
            # 5. Validate Items
            # ==========================================

            if not items:
                raise ValueError(
                    "At least one product is required."
                )

            # ==========================================
            # 6. Create Sale
            # ==========================================

            sale_id = sales_model.create_sale(
                customer_id,
                sale_date,
                remarks,
                discount,
                items
            )

            # ==========================================
            # 7. Success
            # ==========================================

            flash(
                "Sale created successfully",
                "success"
            )

            return redirect(
                url_for("sales.list_sales")
            )

        except ValueError as ex:

            flash(
                str(ex),
                "danger"
            )

        except Exception as ex:

            traceback.print_exc()

            flash(
                "Something went wrong: " + str(ex),
                "danger"
            )

        # ==========================================
        # Reload Sale Page After Error
        # ==========================================

        customers = customer_model.get_customers()

        products = product_model.get_products()

        return render_template(
            "sales/sale_create.html",
            customers=customers,
            products=products,
            today=today
        )

    # ==============================================
    # GET REQUEST
    # ==============================================

    customers = customer_model.get_customers()

    products = product_model.get_products()

    return render_template(
        "sales/sale_create.html",
        customers=customers,
        products=products,
        today=today
    )

@sales_bp.route("/sales/view/<int:sale_id>", methods=["GET"])
def sale_view(sale_id):
    company = company_model.get_company()
    sale, items = sales_model.get_sale_by_id(sale_id)

    sale["amount_in_words"] = (
    num2words(
        sale["total_amount"],
        lang="en_IN"
    ).title()
    + " Only"
)

    gst_amount = float(sale.get("gst_amount") or 0)
    if not gst_amount:
        gst_amount = 0
        for item in items:
            gst_amount += float(item.get("line_total") or 0) * float(item.get("tax_rate") or 0) / 100.0
    sale["gst_amount"] = gst_amount

    return render_template(
        "sales/sale_view.html",
        sale=sale,
        items=items,
        company=company
    )

# @sales_bp.route("/sales/delete/<int:sale_id>")
# def delete_sale(sale_id):
#     sales_model.delete_sale(sale_id)
#     flash("Sale deleted successfully", "success")
#     return redirect(url_for("sales.list_sales"))
@sales_bp.route("/sales/cancel/<int:sale_id>", methods=["POST"])
def cancel_sale(sale_id):

    try:
        sales_model.cancel_sale(sale_id)
        write_audit("CANCEL", "sales", "sale", sale_id)
        flash("Sale cancelled successfully.", "warning")

    except ValueError as ex:
        flash(str(ex), "warning")

    except Exception:
        flash("Could not cancel this sale.", "danger")

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

    try:

        # ==========================================
        # 1. Validate Sale
        # ==========================================

        sale, existing_items = sales_model.get_sale_by_id(id)

        if not sale:
            raise ValueError("Sale not found.")

        if sale.get("sale_status") == "Cancelled":
            raise ValueError(
                "Cancelled sale cannot be edited."
            )

        # ==========================================
        # 2. Get Form Data
        # ==========================================

        customer_id = request.form["customer_id"]

        discount = float(
            request.form.get("discount", 0)
        )

        product_ids = request.form.getlist(
            "product_id[]"
        )

        qtys = request.form.getlist(
            "qty[]"
        )

        prices = request.form.getlist(
            "price[]"
        )

        # ==========================================
        # 3. Validate & Prepare Items
        # ==========================================

        items = []

        for i in range(len(product_ids)):

            if not product_ids[i]:
                continue

            qty = int(qtys[i])
            price = float(prices[i])

            if qty <= 0:
                raise ValueError(
                    "Quantity must be greater than zero."
                )

            if price < 0:
                raise ValueError(
                    "Price cannot be negative."
                )

            items.append({
                "product_id": product_ids[i],
                "qty": qty,
                "price": price
            })

        # ==========================================
        # 4. Validate Items
        # ==========================================

        if not items:
            raise ValueError(
                "At least one product is required."
            )

        # ==========================================
        # 5. Validate Discount
        # ==========================================

        if discount < 0 or discount > 100:
            raise ValueError(
                "Discount must be between 0% and 100%."
            )

        sales_model.update_sale(
            id,
            customer_id,
            discount,
            items
        )

        # ==========================================
        # 8. Success
        # ==========================================

        flash(
            "Sale updated successfully!",
            "success"
        )

        return redirect(
            url_for("sales.list_sales")
        )

    except ValueError as ex:

        flash(
            str(ex),
            "danger"
        )

        return redirect(
            url_for(
                "sales.sale_edit",
                id=id
            )
        )

    except Exception as ex:

        traceback.print_exc()

        flash(
            "Unable to update sale: " + str(ex),
            "danger"
        )

        return redirect(
            url_for(
                "sales.sale_edit",
                id=id
            )
        )


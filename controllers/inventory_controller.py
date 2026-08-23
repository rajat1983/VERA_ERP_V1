from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import inventory_model, product_model
from utils.audit import write_audit

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/stock")
def stock_on_hand():
    search = request.args.get("q", "")
    rows = inventory_model.get_stock_on_hand(search)
    low = sum(1 for r in rows if (r.get("stock_qty") or 0) <= (r.get("threshold") or 0))
    out = sum(1 for r in rows if (r.get("stock_qty") or 0) <= 0)
    value = sum(float(r.get("stock_value") or 0) for r in rows)
    return render_template(
        "inventory/stock.html",
        rows=rows,
        q=search,
        product_count=len(rows),
        low_count=low,
        out_count=out,
        stock_value=value,
    )


@inventory_bp.route("/stock/low")
def low_stock():
    rows = inventory_model.get_low_stock()
    return render_template("inventory/low.html", rows=rows)


@inventory_bp.route("/stock/adjust", methods=["GET", "POST"])
def adjust_stock():
    products = product_model.get_products()
    if request.method == "POST":
        try:
            inventory_model.adjust_stock(
                request.form["product_id"],
                request.form.get("direction", "in"),
                request.form.get("quantity", 0),
                request.form.get("reason", ""),
            )
            write_audit(
                "STOCK_ADJUSTMENT",
                "inventory",
                "product",
                int(request.form["product_id"]),
                request.form.get("reason", "")[:200],
            )
            flash("Stock adjustment saved.", "success")
            return redirect(url_for("inventory.stock_on_hand"))
        except (ValueError, TypeError) as e:
            flash(str(e), "warning")
        except Exception:
            flash("Could not save the adjustment.", "danger")
    return render_template(
        "inventory/adjust.html",
        products=products,
        today=date.today().isoformat(),
    )


@inventory_bp.route("/stock-movements")
def list_movements():
    page = int(request.args.get("page", 1))
    search = request.args.get("q", "")
    per_page = 20
    offset = (page - 1) * per_page
    rows = inventory_model.get_movements(search, per_page, offset)
    total = inventory_model.get_movement_count(search)
    total_pages = (total + per_page - 1) // per_page if total else 1
    return render_template(
        "inventory/movements.html",
        rows=rows,
        page=page,
        total_pages=total_pages,
        q=search,
        total=total,
    )

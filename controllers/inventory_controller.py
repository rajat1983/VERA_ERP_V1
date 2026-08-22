from flask import Blueprint, render_template, request

from models import inventory_model

inventory_bp = Blueprint("inventory", __name__)


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

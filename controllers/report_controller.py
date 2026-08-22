from datetime import date, timedelta

from flask import Blueprint, render_template, request

from models import report_model

report_bp = Blueprint("report", __name__)


def _range():
    to_date = request.args.get("to_date") or date.today().isoformat()
    from_date = request.args.get("from_date") or (date.today() - timedelta(days=30)).isoformat()
    return from_date, to_date


@report_bp.route("/reports")
def index():
    from_date, to_date = _range()
    return render_template("reports/index.html", from_date=from_date, to_date=to_date)


@report_bp.route("/reports/sales")
def sales():
    from_date, to_date = _range()
    return render_template(
        "reports/table.html",
        title="Sales Report",
        from_date=from_date,
        to_date=to_date,
        headers=["Invoice", "Date", "Customer", "Discount %", "GST", "Total", "Sale Status", "Payment"],
        rows=report_model.sales_report(from_date, to_date),
        keys=["invoice_no", "sale_date", "customer_name", "discount", "gst_amount", "total_amount", "sale_status", "payment_status"],
    )


@report_bp.route("/reports/purchases")
def purchases():
    from_date, to_date = _range()
    return render_template(
        "reports/table.html",
        title="Purchase Report",
        from_date=from_date,
        to_date=to_date,
        headers=["Purchase No", "Date", "Vendor", "Discount %", "GST", "Total", "Status"],
        rows=report_model.purchase_report(from_date, to_date),
        keys=["purchase_no", "purchase_date", "vendor_name", "discount", "gst_amount", "total_amount", "status"],
    )


@report_bp.route("/reports/stock")
def stock():
    from_date, to_date = _range()
    return render_template(
        "reports/table.html",
        title="Stock Report",
        from_date=from_date,
        to_date=to_date,
        headers=["SKU", "Name", "Qty", "Reorder", "Cost", "Selling", "Status"],
        rows=report_model.stock_report(),
        keys=["sku", "name", "stock_qty", "reorder_level", "cost_price", "selling_price", "status"],
    )


@report_bp.route("/reports/low-stock")
def low_stock():
    from_date, to_date = _range()
    return render_template(
        "reports/table.html",
        title="Low Stock Report",
        from_date=from_date,
        to_date=to_date,
        headers=["SKU", "Name", "Qty", "Reorder", "Threshold"],
        rows=report_model.low_stock_report(),
        keys=["sku", "name", "stock_qty", "reorder_level", "threshold"],
    )


@report_bp.route("/reports/payments")
def payments():
    from_date, to_date = _range()
    return render_template(
        "reports/table.html",
        title="Payments Report",
        from_date=from_date,
        to_date=to_date,
        headers=["Date", "Amount", "Mode", "Reference", "Invoice", "Customer"],
        rows=report_model.payment_report(from_date, to_date),
        keys=["payment_date", "amount", "payment_mode", "reference_no", "invoice_no", "customer_name"],
    )

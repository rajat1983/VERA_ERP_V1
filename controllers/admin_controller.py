from flask import Blueprint, flash, redirect, render_template, request, url_for
from models import admin_model
from utils.audit import write_audit
from utils.auth import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def utilities():
    return render_template("admin/utilities.html")


@admin_bp.route("/admin/clear-transactions", methods=["POST"])
@admin_required
def clear_transactions():
    try:
        admin_model.clear_transaction_data()
        write_audit("DEACTIVATE", "admin", "transactions", None, "clear transactions")
        flash("Transaction data cleared.", "success")
    except Exception:
        flash("Could not clear transactions.", "danger")
    return redirect(url_for("dashboard.dashboard"))


@admin_bp.route("/admin/reset-database", methods=["POST"])
@admin_required
def reset_database():
    try:
        admin_model.reset_database()
        write_audit("DEACTIVATE", "admin", "database", None, "reset database")
        flash("Database reset complete.", "success")
    except Exception:
        flash("Could not reset the database.", "danger")
    return redirect(url_for("dashboard.dashboard"))

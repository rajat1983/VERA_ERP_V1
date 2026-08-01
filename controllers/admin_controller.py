from flask import Blueprint, flash, redirect, url_for
from models import admin_model

admin_bp = Blueprint(
    "admin",
    __name__
)
@admin_bp.route("/admin/clear-transactions")

def clear_transactions():

    try:

        admin_model.clear_transaction_data()

        flash(
            "Transaction data cleared successfully.",
            "success"
        )

    except Exception as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(url_for("dashboard.index"))
@admin_bp.route("/admin/reset-database")

def reset_database():

    try:

        admin_model.reset_database()

        flash(
            "Database reset successfully.",
            "success"
        )

    except Exception as e:

        flash(
            str(e),
            "danger"
        )

    return redirect(url_for("dashboard.index"))
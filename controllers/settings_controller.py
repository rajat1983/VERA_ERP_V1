from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import company_model
from utils.audit import write_audit
from utils.auth import admin_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def company_settings():
    if request.method == "POST":
        try:
            company_model.save_company(request.form)
            write_audit("UPDATE", "settings", "company", None, "company settings")
            flash("Company settings saved.", "success")
            return redirect(url_for("settings.company_settings"))
        except Exception:
            flash("Could not save company settings. Check required company columns.", "danger")
    return render_template("settings/company.html", company=company_model.get_company() or {})

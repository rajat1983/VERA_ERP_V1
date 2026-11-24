from flask import Blueprint, current_app, render_template

from models import platform_settings_model

legal_bp = Blueprint("legal", __name__, url_prefix="/legal")


def _ctx():
    return {
        "support_email": platform_settings_model.get_value("support_email")
        or current_app.config.get("SUPPORT_EMAIL")
        or "support@vera-erp.local",
        "platform_name": "VERA ERP",
    }


@legal_bp.route("/terms")
def terms():
    return render_template("legal/terms.html", **_ctx())


@legal_bp.route("/privacy")
def privacy():
    return render_template("legal/privacy.html", **_ctx())


@legal_bp.route("/refund")
def refund():
    return render_template("legal/refund.html", **_ctx())

from flask import Blueprint, jsonify, render_template, request, session

from models import company_model, pos_model
from utils.audit import write_audit

pos_bp = Blueprint("pos", __name__)


def _user_id():
    return session.get("user_id")


@pos_bp.route("/pos")
def index():
    company = company_model.get_company() or {}
    return render_template(
        "pos/index.html",
        company=company,
        session_info=pos_model.current_session(_user_id()),
        categories=pos_model.categories(),
    )


@pos_bp.route("/pos/catalog")
def catalog():
    kind = request.args.get("kind", "product")
    category = request.args.get("category", "")
    search = request.args.get("q", "")
    return jsonify(pos_model.catalog(kind, category, search))


@pos_bp.route("/pos/session")
def session_status():
    return jsonify(pos_model.current_session(_user_id()) or {})


@pos_bp.route("/pos/session/start", methods=["POST"])
def session_start():
    if not _user_id():
        return jsonify(ok=False, error="Sign in required."), 401
    info = pos_model.start_session(_user_id())
    write_audit("CREATE", "pos", "session", info.get("id"), "start day")
    return jsonify(ok=True, session=info)


@pos_bp.route("/pos/complete", methods=["POST"])
def complete():
    data = request.get_json(silent=True) or {}
    try:
        result = pos_model.complete_sale(
            _user_id(),
            data.get("customer_id"),
            data.get("items") or [],
            data.get("discount_amount") or 0,
            data.get("payment_mode") or "cash",
            data.get("payments") or [],
        )
    except ValueError as ex:
        return jsonify(ok=False, error=str(ex)), 400
    except Exception:
        return jsonify(ok=False, error="Could not complete the sale."), 400
    write_audit("CREATE", "pos", "sale", result["id"], result["bill_no"])
    return jsonify(ok=True, **result)

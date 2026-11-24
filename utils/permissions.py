from flask import abort, request, session

from utils.auth import auth_enabled
import re


def current_role():
    return (session.get("role") or "").strip().lower()


def can(action, module="*"):
    """
    admin: everything
    manager: view/create/edit/print/pay/adjust; no delete/cancel/admin/users
    staff: view all + sales create/edit/print
    """
    if not auth_enabled():
        return True
    role = current_role()
    action = (action or "").lower()
    module = (module or "*").lower()
    if role == "admin":
        return True
    if action in ("delete", "cancel", "admin", "users"):
        return False
    if role == "manager":
        return action in ("view", "create", "edit", "print", "export", "pay", "adjust")
    if role == "staff":
        if action in ("view", "print", "export"):
            return True
        if module == "sales" and action in ("create", "edit"):
            return True
        return False
    return False


def _staff_write_allowed(path):
    if path == "/sales/add":
        return True
    if path == "/sales/quick-customer":
        return True
    if path in ("/pos/complete", "/pos/session/start"):
        return True
    if re.fullmatch(r"/sales/\d+/update", path):
        return True
    return False


def _staff_form_blocked(path):
    if path.startswith("/sales/add") or re.fullmatch(r"/sales/\d+/edit", path):
        return False
    if path in ("/add", "/create", "/update") or path.startswith("/edit/"):
        return True
    for prefix in (
        "/customer/add",
        "/customer/edit",
        "/vendors/add",
        "/vendors/edit",
        "/products/add",
        "/products/edit",
        "/services/add",
        "/services/",
        "/purchases/add",
        "/purchases/edit",
        "/production/add",
        "/stock/adjust",
        "/settings",
        "/admin",
        "/users",
    ):
        if path.startswith(prefix):
            return True
    return False


def enforce_request():
    if not auth_enabled():
        return
    if request.endpoint in (
        None,
        "static",
        "healthz",
        "auth.login",
        "auth.logout",
        "auth.register",
        "auth.signup",
        "auth.activate",
        "platform.login",
        "platform.logout",
        "billing.expired",
        "billing.home",
        "billing.create_order",
        "billing.verify",
        "billing.webhook",
        "legal.terms",
        "legal.privacy",
        "legal.refund",
    ):
        return
    role = current_role()
    path = request.path if request.path != "/" else "/"
    method = request.method

    if role == "admin":
        return

    if path == "/profile" or path.startswith("/profile"):
        return

    if path.startswith("/admin") or path.startswith("/users") or path.startswith("/settings"):
        abort(403)

    if "/delete" in path or "/cancel/" in path or path.rstrip("/").endswith("/cancel"):
        abort(403)

    if role == "manager":
        return

    # staff
    if method in ("GET", "HEAD"):
        if _staff_form_blocked(path) and path != "/sales/add" and not re.fullmatch(r"/sales/\d+/edit", path):
            abort(403)
        return

    if method == "POST" and _staff_write_allowed(path):
        return

    abort(403)

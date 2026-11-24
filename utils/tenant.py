from flask import g, has_app_context, has_request_context, session


def is_platform_user():
    if not has_request_context():
        return False
    return bool(session.get("platform_user_id"))


def current_tenant_id():
    if has_request_context():
        tid = getattr(g, "tenant_id", None)
        if tid:
            return int(tid)
        tid = session.get("tenant_id")
        if tid:
            return int(tid)
    raise RuntimeError("No tenant in session.")


def bind_shop_session(user, tenant):
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["full_name"] = user.get("full_name") or user["username"]
    session["photo"] = user.get("photo")
    session["role"] = user.get("role") or "staff"
    session["tenant_id"] = int(tenant["id"])
    session["shop_code"] = tenant["shop_code"]
    session.permanent = True
    if has_app_context():
        g.tenant_id = int(tenant["id"])


def bind_platform_session(platform_user):
    session.clear()
    session["platform_user_id"] = platform_user["id"]
    session["platform_email"] = platform_user["email"]
    session["full_name"] = platform_user.get("full_name") or platform_user["email"]
    session["role"] = "platform"
    session.permanent = True

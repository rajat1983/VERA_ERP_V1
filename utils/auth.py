import os
import secrets
from functools import wraps

from flask import session, redirect, url_for, request, abort


OPEN_ENDPOINTS = {"auth.login", "static"}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_hex(16)
        session["_csrf"] = token
    return token


def validate_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not sent or sent != session.get("_csrf"):
            abort(400)


def auth_enabled():
    return os.environ.get("VERA_AUTH", "1") != "0"

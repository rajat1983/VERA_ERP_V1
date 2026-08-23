import os
import secrets
from functools import wraps
from urllib.parse import urlparse

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


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if auth_enabled() and session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def safe_next(path, fallback="/dashboard"):
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return fallback
    return path


def safe_referer(fallback="/dashboard"):
    """Previous page path, same host only. Avoids looping on the blocked URL."""
    ref = request.referrer
    if not ref:
        return fallback
    parsed = urlparse(ref)
    host = (parsed.netloc or "").split("@")[-1]
    if host and host != request.host:
        return fallback
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    dest = safe_next(path, fallback)
    here = request.path or "/"
    if dest.split("?", 1)[0].rstrip("/") == here.rstrip("/"):
        return fallback
    return dest

import os

INSECURE_SECRETS = {
    "",
    "insecure-dev-key",
    "changeme",
    "secret",
    "dev",
    "password",
}


def is_production():
    return os.environ.get("VERA_ENV", "").lower() == "production"


def assert_production_safe():
    if not is_production():
        return
    if os.environ.get("VERA_AUTH", "1") == "0":
        raise SystemExit("VERA_AUTH cannot be disabled when VERA_ENV=production.")
    if os.environ.get("FLASK_DEBUG", "0") == "1":
        raise SystemExit("FLASK_DEBUG cannot be enabled when VERA_ENV=production.")
    key = (os.environ.get("SECRET_KEY") or "").strip()
    if key in INSECURE_SECRETS:
        raise SystemExit("SECRET_KEY must be a non-default value when VERA_ENV=production.")
    for name in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        if not (os.environ.get(name) or "").strip():
            raise SystemExit("%s must be set when VERA_ENV=production." % name)

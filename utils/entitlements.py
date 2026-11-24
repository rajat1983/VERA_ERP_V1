FEATURE_PATHS = (
    ("pos", ("/pos",)),
    ("production", ("/production",)),
    ("services", ("/services",)),
)


def from_access(access):
    access = access or {}
    return {
        "pos": bool(access.get("allow_pos", True)),
        "production": bool(access.get("allow_production", True)),
        "services": bool(access.get("allow_services", True)),
        "max_users": int(access.get("max_users") or 5),
    }


def feature_for_path(path):
    path = path or ""
    for feature, prefixes in FEATURE_PATHS:
        for prefix in prefixes:
            if path == prefix or path.startswith(prefix + "/"):
                return feature
    return None

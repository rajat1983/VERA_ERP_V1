# VERA ERP — local deployment (DDEV)

```bash
ddev start
```

App: `https://vera-erp.ddev.site:5001/`

Local env (`.ddev/config.yaml`): `FLASK_DEBUG=1`, local `SECRET_KEY`, login hint on.

After `web_environment` changes: `ddev restart`.

Production checklist:

- Copy `.env.example` and set a unique `SECRET_KEY`
- `FLASK_DEBUG=0`, `VERA_SHOW_DEFAULT_LOGIN=0`, `VERA_COOKIE_SECURE=1`
- `GET /healthz` should return `{"status":"ok"}` without login
- Backup MariaDB on a schedule (`ddev snapshot` locally; mysqldump in production)
- Point `VERA_LOG_FILE` at a writable log if you need file logs
- Do not use the nested `python-mysql-ddev/` tree

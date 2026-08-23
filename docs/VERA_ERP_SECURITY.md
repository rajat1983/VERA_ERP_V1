# VERA ERP — security

## In place

- Werkzeug password hashes
- Session login; `VERA_AUTH=0` disables auth (dev only)
- CSRF on POST (`csrf_token` / `X-CSRF-Token`)
- HttpOnly + SameSite=Lax cookies; `VERA_COOKIE_SECURE=1` for HTTPS-only
- 8h idle timeout (`VERA_IDLE_SECONDS`)
- Open-redirect guard on `next`
- Login lockout 5 failures / 15 minutes (in-process)
- Destructive admin and cancel via POST
- `FLASK_DEBUG` defaults to **0**; DDEV sets `1` locally
- `SECRET_KEY` required for production; DDEV has a local-only value

## Required before production

- Unique `SECRET_KEY`; never `insecure-dev-key`
- `FLASK_DEBUG=0`, `VERA_SHOW_DEFAULT_LOGIN=0`, `VERA_COOKIE_SECURE=1`
- Change default `admin` password
- Role-based authorization (not implemented)
- Shared rate-limit store if multiple workers
- Upload MIME/size checks review
- IDOR tests on all `/<id>` routes

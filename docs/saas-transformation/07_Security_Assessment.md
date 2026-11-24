# 07 — Security Assessment (SaaS)

Findings are from current code. SaaS **amplifies** single-tenant bugs into cross-shop incidents.

## Actual vulnerabilities (today)

| Sev | Finding | Location | SaaS implication |
|---|---|---|---|
| Critical | Seeded `admin/admin123`, `manager/manager123`, `staff/staff123` | `models/user_model.py` `ensure_default_admin` | First tenant (and copies) share known passwords |
| Critical | `SECRET_KEY` fallback `insecure-dev-key` | `app.py` | Forged sessions **across all shops** on one host |
| High | GET deletes (CSRF) | `/products/delete`, `/customer/delete`, `/vendors/delete`, `/delete/<id>` employees | One malicious page can delete **whichever shop the admin is logged into** |
| High | Product upload: no type/size/unique name | `product_controller.py` | Tenant A overwrite / malware in shared `static/uploads` |
| High | Credentials in repo `root/root` | `db.py` | Production leak if the same file is deployed |
| High | DOM XSS via `innerHTML` | `templates/customer/list.html`, `static/js/vendor.js`, `templates/index.html`, `genai/static/ai.js` | Stored XSS in Shop A could target that shop’s users (and Super Admin if they ever open shop UI) |
| Medium | Staff sees costs, purchases, all users, all AI history | `permissions.py`, `sales_controller.py`, `ai_controller.py` | Wrong once shops have untrusted clerks |
| Medium | Lockout uses `X-Forwarded-For` in-memory | `utils/audit.py` | Trivial bypass on a public SaaS login |
| Medium | `SESSION_COOKIE_SECURE` default 0 | `app.py` | Cookie theft on HTTP |
| Medium | `VERA_AUTH=0` disables login, CSRF, RBAC | `utils/auth.py` | Kill switch must not exist in SaaS prod |
| Low | Unpinned `requirements.txt`; product add flashes raw exceptions | `product_controller.py` | Info leak |

**SQL injection:** not found in application queries (parameterized `%s`). Keep it that way when adding `tenant_id`.

## New SaaS-specific risks (must design against)

| Risk | Control |
|---|---|
| Cross-tenant IDOR (`/sales/view/17`) | Tenant check on every id fetch; tests with two shops |
| Super Admin looking at shop invoices | MVP: metadata only; if later “impersonate”, full audit + time-box + watermark |
| Webhook forgery | Verify Razorpay signature; reject unsigned |
| Tenant_id tampering in POST | Ignore client tenant_id; session only |
| Expired shop using old JS hitting `/pos/complete` | Middleware on **all** POST APIs |
| Platform vs shop role mix-up | Separate `platform_users` table and `/platform/login` |
| Shop wipe | Remove global `reset-database` or Super Admin + tenant filter |
| Registration abuse | Rate limit + email verify + captcha P6 |
| Privacy (DPDP / shop data) | DPA, per-tenant export/delete process, no shared GenAI history |

## Controls required before first paying shop

1. Refuse boot without `SECRET_KEY` and `VERA_COOKIE_SECURE=1` behind HTTPS.
2. No default passwords; platform user from env `PLATFORM_BOOTSTRAP_EMAIL`.
3. POST+CSRF for all deletes; GET delete routes removed.
4. Upload allowlist + size + tenant folder.
5. Escape all live-search DOM (reuse POS `escapeHtml`).
6. Login lockout: Redis/DB, key = account not spoofable header.
7. Subscription middleware (expired shops cannot call ERP APIs).
8. Isolation test suite (two tenants) in CI.
9. `healthz` may stay public; it must not dump tenant data.

## Privacy / legal (commercial)

- Terms of service, privacy policy, refund policy (static pages) before taking payment.
- Platform GST invoicing for subscriptions.
- Shop GST data belongs to the tenant; Super Admin access policy in writing.
- India DPDP: purpose limitation, deletion on tenant offboarding after retention.

## Nested tree

`python-mysql-ddev/app.py` (`secret123`, `debug=True`) must **never** be deployed. Document as out of support.

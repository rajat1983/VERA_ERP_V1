# 01 — Current System Audit

**Status:** Planning only. No application, database, or configuration was changed.  
**Scope:** Live root app (`app.py`, `controllers/`, `models/`, `utils/schema.py`). Nested `python-mysql-ddev/` is a stale copy and is not the product.  
**Date:** 24 Nov 2026.

## 1. Executive snapshot

VERA ERP is a **single-tenant Flask + Jinja2 + MariaDB** application for one stationery/wholesale shop. It already runs operational loops (masters, sales, POS, purchases, stock, AR/AP, reports). It has **no shop identifier, no tenant filter, no subscription, and no platform operator surface**.

Selling subscriptions to many shops requires a new platform layer **around** this app, then a systematic `tenant_id` (and later `branch_id`) cut through every query. It is not a configuration change.

## 2. Architecture (as implemented)

| Layer | Evidence |
| --- | --- |
| Entry | `app.py` — Flask app, `ensure_schema()`, `ensure_roles_users()`, `_guard` (login, CSRF, idle timeout, RBAC) |
| HTTP | Blueprints registered from `controllers/*` (not `routes/*.py`, which are unused duplicates) |
| DB | `db.py` — one connection: host `db`, database `vera_erp`, user `root` / `root` |
| Company | `models/company_model.py` — `SELECT * FROM company LIMIT 1` |
| Auth | `controllers/auth_controller.py` — session keys: `user_id`, `username`, `full_name`, `photo`, `role` (no tenant) |
| RBAC | `utils/permissions.py` — hardcoded `admin` / `manager` / `staff`. Path `admin` today means **shop admin**, not platform owner |
| Schema | `utils/schema.py` — additive ALTER/CREATE. Does **not** create core masters (`products`, `sales`, `customers`, `vendors`, `company`) |
| Frontend | Server-rendered Jinja, Bootstrap 5.3.3 CDN, `templates/base.html` shell |
| Runtime | DDEV (`.ddev/config.yaml`), ports 5000/5001. No root Dockerfile, no CI |

There is **no** `tenant_id`, `shop_id`, `company_id` FK, `branch_id`, or subscription table in Python models.

## 3. Route inventory (live)

| Blueprint | File | Representative paths |
| --- | --- | --- |
| auth | `controllers/auth_controller.py` | `/login`, `/register`, `/activate/<token>`, `/logout` |
| employee | `controllers/employee_controller.py` | `/list`, `/add`, `/create`, `/edit/<id>`, `/delete/<id>` (GET) |
| product | `controllers/product_controller.py` | `/products`, add/edit/view, `/products/categories`, GET delete |
| vendor | `controllers/vendor_controller.py` | `/vendors`, `/api/vendors/search`, `/api/vendors/add`, GET delete |
| customer | `controllers/customer_controller.py` | `/customers`, `/customer/add`, GET delete, `/sales/quick-customer` (sales BP) |
| sales | `controllers/sales_controller.py` | `/sales`, `/sales/add`, view/edit/update, POST cancel |
| pos | `controllers/pos_controller.py` | `/pos`, `/pos/catalog`, `/pos/session/start`, `/pos/complete` |
| purchase | `controllers/purchase_controller.py` | `/purchases`, add/edit/view, POST cancel |
| production | `controllers/production_controller.py` | `/production`, add, POST cancel |
| inventory | `controllers/inventory_controller.py` | `/stock`, `/stock/low`, `/stock/adjust`, `/stock-movements` |
| payment | `controllers/payment_controller.py` | `/payments`, POST `/payments/add`, `/payments/vendor` |
| report | `controllers/report_controller.py` | `/reports/*` + `?export=csv` |
| settings | `controllers/settings_controller.py` | `/settings` (`@admin_required` = shop admin) |
| users | `controllers/user_controller.py` | `/users`, add/edit/approve, `/profile` |
| services | `controllers/service_controller.py` | `/services`, categories, CRUD |
| admin | `controllers/admin_controller.py` | `/admin`, clear-transactions, reset-database |
| dashboard | `controllers/dashboard_controller.py` | `/dashboard` |
| genai | `genai/routes/ai_routes.py` | `/genai/`, `/genai/chat`, `/genai/history` |
| app | `app.py` | `/healthz` |

## 4. What already works (reuse)

- Invoice numbering with `GET_LOCK` (`models/sales_model.py`).
- Sales/purchase GST via `utils/totals.py` and product `tax_rate` / `hsn_code`.
- POS till (`pos_sales`, `pos_payments`) with stock `FOR UPDATE`.
- Inventory on-hand, low stock, adjustments, movements.
- AR (`payments`) and AP (`vendor_payments`) with Partial/Paid.
- CSRF on POST (`utils/auth.py`), Werkzeug password hashes, HttpOnly session cookie.
- Three shop roles (admin/manager/staff) as a **starting** permission model.
- Product categories + service categories with quick-add.
- Company GSTIN and invoice header from `company`.
- Audit log table (`audit_log`) and `utils.audit.write_audit` (partial coverage).
- Email helper `utils/mailer.py` (Mailpit/SMTP) for registration mail.

## 5. Gaps that block SaaS (must fix before selling)

| Gap | Evidence | SaaS impact |
| --- | --- | --- |
| No tenant key | All `SELECT`/`INSERT` unscoped | Shop A would see Shop B’s invoices |
| `company LIMIT 1` | `company_model.py` | Cannot store N shop profiles |
| Session has no tenant | `auth_controller.py` login | Cannot bind requests to a shop |
| Role name `admin` | `permissions.py` | Collides with platform Super Admin |
| POS vs `sales` split | `pos_model.py` vs `dashboard_model.py` | Platform revenue reports would undercount |
| GET deletes | product/customer/vendor/employee | CSRF; worse once shops share a domain |
| Seed passwords | `user_model.ensure_default_admin` | Every new deploy ships `admin/admin123` |
| Schema bootstrap incomplete | `utils/schema.py` | Cannot provision a tenant DB from code alone |
| Username UNIQUE globally | `users.username` | Two shops cannot both have `admin` |
| SKU uniqueness likely global | `products.sku` usage | Collision across shops |
| Nested duplicate app | `python-mysql-ddev/` | Dual maintenance; insecure `secret123` |

## 6. Data model reality

`ensure_schema()` creates or alters: `roles`, `users`, `payments`, `vendor_payments`, `audit_log`, `product_categories`, POS tables, `services`, `service_categories`, plus ALTERs on existing `sales`, `purchases`, `products`, `production_batches`, `stock_movements`.

**Not created by schema (assumed already in MariaDB):** `products` core columns, `customers`, `vendors`, `sales`/`sale_items`, `purchases`/`purchase_items`, `company`, `employees`, `production_batches` core, `production_materials`, `product_recipes`, `ai_chat_history`.

SaaS provisioning **must** replace “hope the dump exists” with a **complete, versioned schema** that includes tenant tables.

## 7. Security baseline (for the SaaS plan)

See `07_Security_Assessment.md`. Highest blockers for a shared platform: seed accounts, GET-delete CSRF, DOM XSS in live search, unscoped staff reads, in-memory lockout, `SECRET_KEY` fallback, product uploads without type/size limits.

## 8. What this audit does not claim

- Live table sizes, indexes, and FK constraints were not dumped from MariaDB.
- Load tests were not run.
- Dependency CVEs were not scanned.
- GenAI quality was not evaluated; `/genai/history` is unscoped and `ai.js` does not send CSRF.

---

**Phase 0 complete.** Architecture recommendation and work plan are in `04_Product_Architecture.md` and `09_Implementation_Roadmap.md`.

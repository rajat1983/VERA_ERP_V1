# 04 — Product Architecture

## Recommended product hierarchy

```
VERA ERP SaaS Platform
├── Level 1  Platform Super Admin     (/platform/*)
├── Level 2  Business registration    (public signup + payment)
├── Level 3  Tenant / shop workspace  (tenant_id)
├── Level 4  Branches                 (branch_id, Phase 5)
├── Level 5  Shop users & roles       (shop_admin / manager / staff)
├── Level 6  ERP modules              (existing Flask app, scoped)
└── Level 7  Subscription & billing   (plans, Razorpay, enforcement)
```

## Recommended tenancy model: **shared database, row isolation**

| Model | Verdict for VERA |
| --- | --- |
| Shared DB + `tenant_id` on every business table | **Recommended MVP and default scale (tens to low thousands of shops)** |
| Database per tenant | Optional later for a large/enterprise shop only (hybrid) |
| Schema per tenant | Rejected — MariaDB ops cost, migrations × N, poor Super Admin analytics |

### Why shared DB

1. Current code is already **one** `vera_erp` database (`db.py`) and PyMySQL models with no connection switcher.
2. Super Admin **must** count shops, revenue, and expiry in one query. That is natural on shared tables with `tenant_id`.
3. Stationery shops are small; thousands of rows per tenant, not billions.
4. Backup is one `mysqldump` plus per-tenant export jobs.
5. Existing single shop migrates to `tenant_id = 1` without splitting MariaDB.

### Why not DB-per-tenant first

- `get_db_connection()` is global. Per-tenant DBs imply a connection router, migration runner per shop, and broken platform reports unless you federate.
- DDEV/production ops for N databases is disproportionate for the first commercial year.

### Hybrid later

Keep shared DB. If one tenant exceeds isolation or compliance needs, **replicate that tenant** to a dedicated database and set `tenants.isolation = dedicated` + connection DSN. Do not design that for month one.

## Tenant identification

| Method | Use |
| --- | --- |
| **Login: shop code + username** | MVP. Fits current `/login` with one extra field. Works on `vera-erp.ddev.site` and a single production host. |
| Subdomain `slug.veraerp.com` | Phase 5. Requires DNS and TLS automation. Session still stores `tenant_id`. |
| Path `/t/slug/` | Avoid. Breaks every existing absolute route (`/sales/add`). |

Resolution order at login:

1. Read `shop_code` (or host subdomain).
2. Load `tenants` where `slug` matches and status allows login.
3. Authenticate `users` where `tenant_id` + username.
4. Check subscription (unless platform user).
5. Set session: `tenant_id`, `user_id`, `shop_role`, `plan_code`, `subscription_status`.

Platform Super Admin uses `/platform/login` and **no** `tenant_id` in session (or `tenant_id = 0` reserved and never used in ERP queries).

## Isolation rules (non-negotiable)

1. **Every** business `SELECT/UPDATE/DELETE` includes `AND tenant_id = %s` with session tenant.
2. Inserts always set `tenant_id` from session, never from the form.
3. Integer URLs (`/sales/view/17`) 404 if tenant mismatch (fixes today’s IDOR).
4. Unique indexes are composite `(tenant_id, …)`.
5. File paths include tenant id.
6. Search APIs (`/product-search`, `/api/vendors/search`, POS catalog) filter tenant.
7. Super Admin queries **aggregates** or shop metadata, not line items, in MVP.
8. Automated tests: create two tenants, assert shop A cannot read shop B SKUs, invoices, or POS bills.

Implementation approach that **avoids a full rewrite**: add `require_tenant()` on `g.tenant_id` in `app.py` `_guard`, then thread `g.tenant_id` into models. A small wrapper around `cursor.execute` that rejects SQL without `tenant_id` for a denylist of tables is a Phase 6 safeguard, not Phase 1.

## Branch policy (future-ready, not MVP)

**Bill the business (tenant), not the branch.**

| Topic | Recommendation |
| --- | --- |
| What a tenant is | Legal shop / GSTIN / paying customer |
| What a branch is | Second counter or godown under the same GSTIN |
| Subscription | One plan per tenant; **branch seat add-on** (price per extra branch) when you sell it |
| Stock | Default **per branch** (`branch_id` on `products` qty is wrong; use `stock_balances(tenant_id, branch_id, product_id)` when branches launch) |
| MVP | `branch_id NULL` = single location; column reserved on movements/sales |

Do not charge a full second subscription per branch unless the customer is a separate legal entity (that is a second tenant).

## Application topology

```
[Browser]
   ├─ /login                → shop users (subscription gated)
   ├─ /platform/login       → Super Admin
   └─ /signup               → new tenant + plan

[Flask]
   ├─ _guard: CSRF, auth, tenant bind, subscription allowlist
   ├─ /platform/*           → platform_bp (new)
   ├─ /billing/*            → shop billing (new)
   └─ existing ERP BPs      → require active subscription + tenant_id

[MariaDB vera_erp]
   ├─ platform_* / tenants / subscriptions / plans / platform_payments
   └─ existing tables + tenant_id
```

## Reuse vs new code

| Keep | New |
| --- | --- |
| All ERP templates and JS | `platform_bp`, `billing_bp` |
| `utils/totals.py` sales GST | `utils/tenant.py`, subscription middleware |
| Shop RBAC as shop_admin/manager/staff | `platform_users` |
| `write_audit` | `tenant_id` column |
| Razorpay not present — new | Webhook endpoint, idempotency keys |

## Existing data migration

1. Insert `tenants` row for the current business (from `company`).
2. `UPDATE` every business table `SET tenant_id = 1` (after adding NOT NULL default).
3. Map current `users.role = admin` → `shop_admin`.
4. Create first `platform_users` **from env**, not `ensure_default_admin`.
5. Disable seeded `admin/admin123` on the shop.
6. Keep `python-mysql-ddev/` unused; do not tenantize it.

## Scalability notes

Shared DB is enough for **hundreds of shops** if indexes start with `tenant_id` and reports are paginated (today several reports are unpaginated — Phase 6). Connection pool (not a new connect per model call) is a Phase 6 performance item; models currently open/close connections per function.

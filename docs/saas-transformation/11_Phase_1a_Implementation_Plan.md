# 11 — Phase 1a Implementation Plan (awaiting approval)

**Status:** Plan only. No code, schema, or config will be applied until you approve this document.  
**Out of scope:** Phase 1b, subscriptions, Razorpay, branches, GL, Super Admin shop management UI (beyond a minimal platform login).

Same MariaDB database as today (`vera_erp` via `db.py`). Additive columns and one new `tenants` table. Existing rows become **tenant 1**.

---

## 1. Goals

1. Persist a **tenant/shop** with a unique **shop code**.
2. Shop login: **shop code + username or email + password**.
3. Super Admin: **separate** `/platform/login` (email + password), never uses shop code, never blocked by tenant rules.
4. Bind every authenticated shop request to `g.tenant_id` from the **session**, never from the client body.
5. Add `tenant_id` on all business tables; backfill the current shop.
6. Enforce isolation on a **representative module: Products** (including categories and `/product-search`).
7. Prove isolation with automated tests (two tenants).
8. Existing shop users, invoices, stock, and POS keep working as tenant 1 (regression).

---

## 2. What we will not do in 1a

- Subscription plans, expiry middleware, Razorpay.
- Tenantize sales, POS, purchases, reports (columns exist; **queries stay unfiltered** because all production data is tenant 1).
- Shop signup / second shop UI (second tenant exists **only in tests**).
- Rename `admin` role to `shop_admin` (unnecessary churn; shop `admin` stays shop-level).
- Rewrite `get_db_connection()` or introduce an ORM.
- Touch `python-mysql-ddev/`.

**Safety:** No production UI to create tenant 2 in 1a, so unscoped sales queries cannot leak live shops.

---

## 3. Database migration strategy

Same database. `utils/schema.py` `ensure_schema()` (existing pattern) plus a dedicated `_ensure_tenants()` so DDEV still bootstraps. Idempotent: safe to run twice.

### 3.1 New table `tenants`

| Column | Type | Notes |
|---|---|---|
| id | INT PK AI | tenant_id elsewhere |
| shop_code | VARCHAR(16) UNIQUE NOT NULL | e.g. `SHOP0001` |
| name | VARCHAR(160) NOT NULL | From current `company.company_name` if present |
| slug | VARCHAR(80) UNIQUE NOT NULL | Lowercase shop_code for later subdomains |
| status | VARCHAR(20) NOT NULL DEFAULT 'active' | active/suspended (no billing yet) |
| created_at | TIMESTAMP | |

Shop code generation: `SHOP` + 4-digit sequence with MariaDB `GET_LOCK('vera_shop_code', 10)` (same idea as invoice numbers). First migrated shop: **`SHOP0001`**.

### 3.2 New table `platform_users` (minimal)

| Column | Type |
|---|---|
| id | INT PK AI |
| email | VARCHAR(120) UNIQUE NOT NULL |
| username | VARCHAR(80) UNIQUE NOT NULL |
| password_hash | VARCHAR(255) NOT NULL |
| full_name | VARCHAR(120) |
| is_active | TINYINT DEFAULT 1 |
| created_at | TIMESTAMP |

Bootstrap: if table empty, create **one** user from env `PLATFORM_BOOTSTRAP_EMAIL` + `PLATFORM_BOOTSTRAP_PASSWORD` (no hardcoded `admin123`). If env unset, **do not** seed; document that platform login is unavailable until env is set.

### 3.3 `tenant_id` on existing tables

Add `tenant_id INT NOT NULL DEFAULT 1` (default only for backfill), then:

1. `UPDATE … SET tenant_id = 1 WHERE tenant_id IS NULL` (if nullable first).
2. Add index `idx_{table}_tenant (tenant_id)`.
3. Leave DEFAULT 1 until Phase 4 unique-index rebuild; **application inserts must still set tenant_id from session**.

**Tables to alter** (if they exist):

| Table | Why |
|---|---|
| users | Shop login scoped to tenant |
| company | Replaces `LIMIT 1` as 1:1 with tenant (query still LIMIT 1 **per tenant** in 1a settings optional) |
| products | Isolation slice |
| product_categories | Isolation slice |
| customers | Future; backfill now |
| vendors | Future; backfill now |
| services | Future |
| service_categories | Future |
| employees | Future |
| sales | Future |
| sale_items | Prefer column even if access is via parent |
| purchases | Future |
| purchase_items | Future |
| payments | Future |
| vendor_payments | Future |
| stock_movements | Future |
| production_batches | Future |
| production_materials | Future |
| product_recipes | If table exists |
| pos_sessions | Future |
| pos_sales | Future |
| pos_sale_items | Future |
| pos_payments | Future |
| audit_log | NULL allowed for platform actors |

**Do not** add tenant_id to: `roles` (global catalog), `subscription_*` (do not exist yet), `platform_users`, `tenants`.

### 3.4 Unique keys in 1a (only where required for login)

- `tenants.shop_code` UNIQUE
- `users`: drop/replace global `username` UNIQUE with **UNIQUE (tenant_id, username)** if a unique index exists. Email unique **per tenant** `(tenant_id, email)` where email is not null — if a global email unique exists, replace it. If no unique index exists today, add the composite unique.

Do **not** rebuild product SKU unique in 1a unless a global unique actually exists (verify `SHOW INDEX` at implement time). If global SKU unique exists, change to `(tenant_id, sku)` in 1a because products are the isolation slice.

### 3.5 Default tenant migration

On first `_ensure_tenants()`:

1. If `tenants` empty, INSERT shop_code `SHOP0001`, name from `company.company_name` or `'VERA Shop'`.
2. `UPDATE` all listed business tables `SET tenant_id=1` (already default).
3. Existing `users` remain; they belong to SHOP0001. **Passwords unchanged.**
4. Stop inserting new `admin/admin123` seeds in `ensure_default_admin` when users already exist; if the table is empty after tenant attach, create shop admin **only** when a dedicated env is set (`SHOP_BOOTSTRAP_*`), not hardcoded `admin123`. Preserve current DDEV users if they already exist.

Rollback: keep DEFAULT 1 so dropping the app code still leaves a working single-tenant DB.

---

## 4. Tenant context and auth middleware

### 4.1 `utils/tenant.py` (new)

- `current_tenant_id()` → `g.tenant_id`
- `is_platform_user()` → session flag
- `bind_shop_session(user, tenant)` — sets `user_id`, `tenant_id`, `shop_code`, `role`, etc.
- `bind_platform_session(platform_user)` — sets `platform_user_id`, **no** `tenant_id`

### 4.2 `app.py` `_guard` (extend, do not replace)

After existing login/CSRF/idle checks:

1. `/platform/login`, `/platform/logout` are public (CSRF on POST).
2. Paths `/platform/*` require `session.platform_user_id`. Shop sessions get 403.
3. Shop ERP paths require `session.user_id` **and** `session.tenant_id`. Copy `tenant_id` onto `g`. If missing, `session.clear()` and redirect to shop login.
4. Shop users hitting `/platform/*` → 403.
5. Platform users hitting ERP (`/sales`, `/products`, …) → 403 (no accidental cross-shop). Super Admin shop data UI is Phase 2.
6. Ignore any `tenant_id` in form/JSON/query.

### 4.3 Shop login (`/login`)

Form fields: `shop_code`, `username` (label: Username or email), `password`.

`user_model.authenticate(shop_code, identifier, password)`:

- Resolve tenant by `shop_code` (status=active).
- Match `users` where `tenant_id=?` AND (`username=?` OR `email=?`).
- Existing password hash check and `login_blocked_reason`.

Session: `tenant_id`, `shop_code`, plus current keys.

### 4.4 Platform login (`/platform/login`) — stub panel

Email + password against `platform_users`. Session without tenant. Landing: simple “Platform (Phase 2)” page so we can test the split. **No** shop list, billing, or Razorpay.

### 4.5 Register / activate (preserve)

`/register` adds required `shop_code`; new users get that `tenant_id` (pending staff, same as today). Activate token unchanged but lookup includes tenant. Prevents attaching users to the wrong shop without the code.

---

## 5. Isolation slice: Products

**Why products:** CRUD + search + categories; used by sales/POS; enough to prove IDOR and list leaks.

All `product_model` SQL that reads/writes `products` or `product_categories`:

- `WHERE tenant_id=%s` on SELECT/UPDATE/DELETE
- INSERT includes `tenant_id`
- `generate_product_code()` scoped to tenant
- `product_name_exists`, `search_categories`, `add_category`, `ensure_category` scoped
- `get_product_by_id` 404 if wrong tenant (controller already flashes not found)

Controllers pass `g.tenant_id` only.

`/product-search` must filter tenant (sales uses this).

**Not in 1a:** product image path prefix (nice-to-have); GET delete remains a known issue (Phase 4/security), but delete still `AND tenant_id=?`.

---

## 6. Affected files

| File | Change |
|---|---|
| `utils/schema.py` | `_ensure_tenants`, ALTER tenant_id on listed tables, unique indexes |
| `utils/tenant.py` | **New** context helpers |
| `app.py` | `_guard` platform vs shop; `g.tenant_id`; register `platform_bp` stub |
| `models/tenant_model.py` | **New** get by code, generate code, get/create default |
| `models/user_model.py` | authenticate(shop_code, identifier, password); unique username/email per tenant; register with tenant; stop hardcoded seeds |
| `models/platform_user_model.py` | **New** authenticate/bootstrap |
| `models/product_model.py` | All queries tenant-scoped |
| `controllers/auth_controller.py` | Shop code on login/register; session bind |
| `controllers/product_controller.py` | Pass tenant_id; 404 cross-tenant |
| `controllers/platform_controller.py` | **New** login/logout/placeholder home |
| `templates/auth/login.html` | Shop code field |
| `templates/auth/register.html` | Shop code field |
| `templates/platform/login.html` | **New** |
| `templates/platform/home.html` | **New** stub |
| `tests/test_tenant_isolation.py` | **New** two-tenant products tests |
| `tests/conftest.py` | **New** DB fixtures if needed |
| `.ddev/config.yaml` | Optional env `PLATFORM_BOOTSTRAP_*` (only if you approve env change; can document instead) |

Unchanged in 1a: sales/POS/purchase/inventory models (rely on all rows = tenant 1).

---

## 7. Tests

### 7.1 Automated (pytest, same DDEV DB, isolated test tenants)

Use shop codes `TESTA` / `TESTB` created in fixture and deleted in teardown (or `tenant_id` high ids). Do not use SHOP0001 production rows for assertions of absence.

| Test | Pass condition |
|---|---|
| Login requires shop code | Missing code → no session |
| Login username+code | SHOP0001 + existing user works |
| Login email+code | Same user via email |
| Wrong shop code | Same username in other tenant does not authenticate |
| Product insert tenant A | Row.tenant_id = A |
| Product list tenant B | Does not include A’s SKU/name |
| `get_product_by_id` as B with A’s id | None / 404 |
| `/product-search` as B | No A products |
| Category quick-add | Category not visible to other tenant |
| Platform login | No `tenant_id` in session; `/products` 403 |
| Shop user `/platform/` | 403 |
| Totals unit tests | Existing `tests/test_totals.py` still pass |

### 7.2 Regression (manual / browser after code)

On SHOP0001 as current admin:

- Login with shop code + username (and once with email)
- Dashboard loads
- Products list shows **same** existing products
- Add product, edit, view
- New sale still finds products via `/product-search`
- POS catalog still lists products (unscoped POS reads all tenant_id=1 rows — OK)
- Purchase, stock, reports unchanged
- Register with SHOP0001 still pending-approval

---

## 8. Acceptance criteria (Phase 1a done)

1. `tenants` contains `SHOP0001` named from current company; all existing business rows have `tenant_id = 1`.
2. Shop login is shop code + username **or** email + password; old username-only login **fails**.
3. Session has `tenant_id`; `g.tenant_id` set on ERP requests; request body cannot override it.
4. `/platform/login` authenticates `platform_users` independently; platform session cannot open `/products`; shop session cannot open `/platform`.
5. Products (CRUD, categories, `/product-search`) never return or mutate another tenant’s rows.
6. Automated isolation tests pass.
7. Existing SHOP0001 ERP flows (sales, POS, purchase, stock, dashboard) still work; no data loss.
8. No subscription, Razorpay, or branch tables/code.
9. No hardcoded `admin123` **newly inserted** by bootstrap (existing hashes untouched).

---

## 9. Implementation sequence (after approval)

1. Schema `_ensure_tenants` + ALTERs + backfill SHOP0001  
2. `tenant.py` + `tenant_model` + shop code generator  
3. User authenticate + login/register templates  
4. `_guard` + platform stub login  
5. Product model/controller tenant_id  
6. Tests + DDEV regression  
7. Stop for **your review** before Phase 1b  

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Unique username index drop fails | Inspect `SHOW INDEX FROM users` first; migrate carefully |
| Email login matches two users | Unique (tenant_id, email); identifier match is tenant-scoped |
| Unscoped sales after a second live tenant | No UI to create tenants in 1a |
| `ensure_schema` swallows errors | `_ensure_tenants` must log and re-raise in dev |
| Platform env not set | Shop ERP still works; platform login shows setup message |

---

**Waiting for approval to implement Phase 1a exactly as above.**

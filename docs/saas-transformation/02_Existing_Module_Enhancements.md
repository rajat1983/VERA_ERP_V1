# 02 — Existing Module Enhancements

Every row is based on current controllers/models. **Priority:** P0 foundation / P1 billing / P2 tenantize ERP / P3 commercial. Do not implement until approved.

Reuse existing screens and business rules. The main change is **scope every query and unique key by tenant**, plus subscription gate on login.

### Existing Module Enhancement

| Module | Current Status | Required Enhancement | Priority | Complexity |
|---|---|---|---|---|
| Dashboard | Functional KPIs from `sales`/`purchases`/`payments` (`services/dashboard/dashboard_service.py`). Ignores POS and cancelled invoices. Date picker does not apply to “today” KPIs. | Filter all SQL by `tenant_id`. Union or post POS into sales so shop dashboards are complete. Exclude cancelled. Apply date range to all widgets. Super Admin sees **platform** KPIs, not this page. | P2 | Medium |
| Authentication & login | Session login (`auth_controller.py`). Register creates pending **staff** for this one shop. No tenant. Role stored in session until logout. | Login must resolve **tenant** (subdomain or shop code + username). Session: `tenant_id`, `branch_id`, `platform_role` vs `shop_role`. Subscription gate: expired → renewal screen, Super Admin never gated. Unique username **per tenant**. Public register becomes **shop signup**, not extra staff. | P1–P2 | High |
| User & role management | Shop users CRUD (`user_controller.py`). Roles admin/manager/staff hardcoded. `@admin_required` = shop admin. | Split **platform users** from **shop users**. Rename shop `admin` → `shop_owner` / `shop_admin` in data (keep UI label “Admin”). Enforce plan **user seats**. Tenant-scoped user list. Do not let shop admin see other shops. | P2 | Medium |
| Company / shop | Single row `company` LIMIT 1 (`company_model.py`). GSTIN, address, product prefix. | One `company` (or `tenants` profile) **per tenant**. Settings stay shop-local. Prefixes (`PRD`, invoice year) unique **per tenant**. No more LIMIT 1. | P2 | Medium |
| Products & categories | CRUD, image, SKU, barcode, GST/HSN, categories + quick-add. `can_delete_product` **missing** (delete 500). GET delete. Product edit writes `stock_qty`. | `tenant_id` on `products`, `product_categories`. Unique `(tenant_id, sku)`, `(tenant_id, barcode)` if barcode set. Stop editing stock on product form (use inventory). POST+CSRF delete + in-use check. Uploads under `uploads/{tenant_id}/products/`. | P2 | Medium |
| Inventory & stock | On-hand from `products.stock_qty`; movements; adjust with `FOR UPDATE`. | All movements and adjusts tenant-scoped. Optional `branch_id` later. Never trust client `tenant_id`. Low-stock reports per shop. | P2 | Medium |
| Purchase & suppliers | Full PO, GST, vendor payments, cancel. Purchase number `MAX(id)+1` race. GET vendor delete. | Tenant-scope vendors and purchases. Unique vendor code and vendor invoice **per tenant**. Lock purchase number generation (copy sales `GET_LOCK`). POST vendor delete. | P2 | Medium |
| Sales | Strongest module: invoice lock, GST, discount %, stock, generated-by, cancel. GST on **pre-discount** line (`utils/totals.py`). | Tenant-scope sales/items. Invoice series per tenant. Keep GST rule unless India GST-after-discount is approved as a **separate** change. Cancel must not leak across shops. | P2 | Medium |
| POS | Isolated `pos_sales` ledger. Catalog = products + services. Day session unique `(user_id, business_date)`. | Tenant-scope sessions, catalog, complete. Unique session `(tenant_id, user_id, business_date)`. **Must appear in shop sales reports** (post into `sales` or union). Feature-flag POS per plan. | P2 | High |
| Customers | Master CRUD, GSTIN, sale quick-add. GET delete, no sales-in-use check. Not CRM. | Tenant-scope. Unique phone/email **per tenant**. POST delete + FK check. Credit limit = P3. | P2 | Low–Med |
| Invoices & payments | Print sale invoice; AR/AP receipts; aging reports. POS cash not in `payments`. | Tenant-scope receipts. Aging per shop. Platform billing invoices are a **new** module (do not reuse `payments.sale_id`). | P2 + new | Medium |
| Accounting & finance | **Not implemented** (no COA, journals). GST is a line tax total only. | Out of MVP SaaS. Keep AR/AP. GL is Phase 5+ and must sit **on** tenant-isolated sales/POS, not before. | P5 | High |
| Expenses | **Not implemented**. | Optional P5. New table `expenses` with `tenant_id`. | P5 | Medium |
| Reports | CSV lists; sales includes cancelled; POS omitted; payables/receivables date filters ignored. | Tenant-scope every query. Exclude cancelled. Include POS. Platform reports are Super Admin only. Export still `can('export')` but **shop-only data**. | P2 | Medium |
| Settings | Company form, shop-admin only. | Shop settings vs **platform settings** (`/platform/...`). Feature flags from subscription. Terms/privacy links. | P2–P3 | Medium |
| Services | CRUD + POS catalog. No GST/HSN. Not on sales invoices. | Tenant-scope `services`, `service_categories`. Keep POS-only unless sales lines gain `item_type`. | P2 | Low |
| Production | Batch create/cancel; recipes if rows exist; no recipe UI; empty BOM still adds FG. | Tenant-scope batches and recipes. Recipe CRUD = P3. Do not sell as MRP until recipes exist. | P2 (scope) / P3 (BOM UI) | Medium |
| Employees | Thin CRUD, GET delete, root paths `/list`. | Tenant-scope. Align URLs with `/employees`. Optional vs Users — avoid two people masters if possible. | P2 | Low |
| Shop admin utilities | Truncate/reset entire DB (`admin_controller.py`). | **Remove or Super-Admin-only with tenant filter.** A shop owner must never `reset-database` for the platform. Shop-level “demo reset” only deletes **that** `tenant_id`. | P1 | Medium |
| GenAI | Chat UI; global history; CSRF likely broken. | Disable for SaaS MVP or tenant-scope history + quota. Never share prompts across shops. | P3 | Medium |

## Cross-cutting changes (every ERP module)

1. **Query helper** — all model functions take `tenant_id` from session (never from request body as the only check).
2. **Unique keys** — `(tenant_id, natural_key)` for sku, username, invoice_no, purchase_no, customer_code, vendor_code, bill_no, category name.
3. **IDOR** — `/sales/view/<id>` must 404 if row.tenant_id != session.tenant_id (today any logged-in user can open any id).
4. **File storage** — prefix by tenant; no overwrite of `secure_filename` originals.
5. **Audit** — `audit_log.tenant_id` + platform actor id for Super Admin impersonation (if ever allowed; default: **no impersonation in MVP**).
6. **POS + sales** — one commercial number for “today’s sales” per shop.

## Explicitly do not rebuild

- Sales line editor, GST % discount UI, POS cart (reuse; wrap with tenant).
- Inventory movement types (`sale`, `purchase`, `pos`, `adjust`).
- Bootstrap theme (`vera-theme.css`, `base.html`) — add a **platform** chrome variant, do not replace shop UI.

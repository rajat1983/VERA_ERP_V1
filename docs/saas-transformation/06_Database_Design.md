# 06 — Database Enhancement Plan

No migrations have been applied. This is the target design for approval.

## Strategy

1. Add **platform tables** (new).
2. Add `tenant_id` (INT NOT NULL) to **every business table**, backfill `1` for the current shop, then tighten unique indexes.
3. Reserve `branch_id` NULLABLE on operational docs (sales, purchases, stock, POS) for Phase 5 — do not build branch UI yet.
4. Replace incomplete `ensure_schema()` with versioned migrations (Alembic or numbered SQL). `utils/schema.py` ALTERs are not enough to provision tenants.

## New tables (platform)

| Existing/New Table | Purpose | Tenant Relationship | Changes |
|---|---|---|---|
| `tenants` | Shop/business workspace | Self (PK) | slug UNIQUE, name, gstin, status, timezone, created_at |
| `platform_users` | Super Admin operators | None | email UNIQUE, password_hash, is_active — **not** `users` |
| `subscription_plans` | Admin-defined plans | None | duration_days, price_paise, gst_rate, max_users, max_branches, features JSON, is_public |
| `subscriptions` | Current (or latest) sub per tenant | `tenant_id` UNIQUE current | plan_id, status, starts_on, ends_on, grace_days |
| `subscription_events` | History | `tenant_id` | type, amount, actor, notes, created_at |
| `platform_invoices` | SaaS tax invoices | `tenant_id` | invoice_no UNIQUE, gst_breakup, pdf_path |
| `platform_payments` | Gateway + manual | `tenant_id`, invoice_id | gateway, gateway_payment_id UNIQUE, status |
| `platform_settings` | Keys, grace, GSTIN | None | key/value |
| `email_templates` | Notification bodies | None | code UNIQUE |
| `coupons` | P5 | Optional tenant | code, percent, valid_until |

## Existing tables — tenant columns

| Existing/New Table | Purpose | Tenant Relationship | Changes |
|---|---|---|---|
| `users` | Shop users only | `tenant_id` NOT NULL | Drop global username UNIQUE; add UNIQUE(`tenant_id`,`username`); `shop_role`; remove seed admin |
| `roles` | Keep seed shop roles | None (catalog) or per tenant | Prefer global catalog shop_admin/manager/staff |
| `company` | Shop profile | `tenant_id` UNIQUE | Remove LIMIT 1 pattern; 1:1 with tenant |
| `products` | Catalog | `tenant_id` | UNIQUE(`tenant_id`,`sku`); barcode unique per tenant if not null |
| `product_categories` | Categories | `tenant_id` | UNIQUE(`tenant_id`,`name`) |
| `customers` | CRM master | `tenant_id` | UNIQUE phone/email per tenant |
| `vendors` | Suppliers | `tenant_id` | UNIQUE vendor_code per tenant |
| `services` / `service_categories` | POS services | `tenant_id` | Composite uniques |
| `employees` | Optional HR | `tenant_id` | Scope |
| `sales` / `sale_items` | Invoices | `tenant_id` on header (items via sale) | UNIQUE(`tenant_id`,`invoice_no`); items inherit via sale_id |
| `pos_sessions` / `pos_sales` / `pos_sale_items` / `pos_payments` | Till | `tenant_id` | UNIQUE session (`tenant_id`,`user_id`,`business_date`); UNIQUE(`tenant_id`,`bill_no`) |
| `purchases` / `purchase_items` | POs | `tenant_id` | UNIQUE(`tenant_id`,`purchase_no`) |
| `payments` | AR | `tenant_id` | Always with sale.tenant_id match |
| `vendor_payments` | AP | `tenant_id` | Match purchase |
| `stock_movements` | Ledger | `tenant_id` | Index (`tenant_id`,`product_id`,`id`) |
| `production_batches` / materials / `product_recipes` | Production | `tenant_id` | Scope recipes |
| `audit_log` | Activity | `tenant_id` NULL for platform | Index tenant+created_at |
| `ai_chat_history` | GenAI | `tenant_id` | Create table if feature kept |

`sale_items` / `purchase_items` / `pos_sale_items` can omit `tenant_id` **only if** every access joins the parent and parent is tenant-checked. Prefer **denormalized tenant_id on lines** for safer deletes and reporting.

## Indexes (minimum)

- `(tenant_id, id)` covering PK access.
- `(tenant_id, sale_date)`, `(tenant_id, invoice_no)`.
- `(tenant_id, sku)`, `(tenant_id, status)` on products.
- `subscriptions(status, ends_on)` for expiry job.

## Constraints

- FK `tenant_id → tenants.id` (ON DELETE RESTRICT). Never cascade-delete a tenant with sales.
- Shop delete = **suspend + anonymize** after legal retention, not DELETE FROM products.

## Sequence numbers

Today: invoice `GET_LOCK` global; purchase `MAX(id)+1`; POS `POSYYYY#####`; product SKU `MAX(id)`.

SaaS: lock name **`vera_invoice_{tenant_id}`** (and peers). Sequences are per tenant.

## Backup

- Nightly full dump of `vera_erp`.
- Weekly per-tenant CSV/SQL export for paid shops (P6).
- Super Admin “download shop backup” = filtered dump WHERE tenant_id=?.

## Migration of current shop

```sql
-- conceptual; not executed
ALTER TABLE products ADD COLUMN tenant_id INT NOT NULL DEFAULT 1;
-- backfill, then drop default, add FK and unique (tenant_id, sku)
```

Run once on the existing DDEV database after Super Admin + tenants exist.

# VERA ERP — current-state audit

Date: 23 Aug 2026  
Branch intended: `VERA_ERP_V3`  
Stack: Flask + Jinja2 + Bootstrap 5 + PyMySQL/MariaDB (DDEV)  
Method: code inspection of repo root (not `python-mysql-ddev/`). No load test.

## Existing modules

| Area | Status |
| --- | --- |
| Auth (login/logout, CSRF, hashed passwords) | Working, Phase 0 hardened |
| Dashboard KPIs/charts | Working from live queries |
| Customers / vendors / products / employees | CRUD working; 360 views partial |
| Sales + invoice print + GST + lock | Working; agreed UI rules preserved |
| Purchase + GST + stock-in | Working |
| Payments against sales | Working; no vendor payables |
| Inventory stock + movements | Working; no adjustment UI |
| Production batches | Create/cancel only; no BOM |
| Reports + CSV | Working; no pagination on large sets |
| Admin clear/reset | POST + confirm |
| GenAI chat blueprint | Present; out of ERP core |

## Completed (verified in code)

- Sales: dropdowns only, Tippy (stock/cost/selling/GST %), discount as %, server `calculate_document_totals`, invoice `GET_LOCK`, cancel reverses stock.
- Purchase: same GST model, stock-in, cancel reverse.
- Payments cannot exceed invoice total (model-enforced).
- Stock ledger table `stock_movements` written on sale/purchase/production.
- UI shell Phases 1–10 of the earlier visual roadmap.

## Partial

- Company row used on invoices; no settings UI.
- Customer/vendor/product history is not a full 360.
- Dashboard has no payables KPI.
- Audit log table + LOGIN/LOGOUT/CANCEL events (Phase 0); not a full before/after trail.

## Broken / risky

- Nested `python-mysql-ddev/` is a stale copy — do not edit it.
- `config.py` duplicates `db.py` and is unused by `app.py`.
- Admin wipe still exists (now POST); no role gate.
- Default admin `admin`/`admin123` if users table empty.

## Business-rule gaps

- No CGST/SGST/IGST (correct per current schema).
- No sales/purchase returns module.
- No AR aging, vendor bills, credit limit enforcement.
- Production does not consume raw materials via BOM.
- Inactive customer/product not consistently blocked on new sales.

## Database gaps

- No roles/permissions tables.
- `audit_log` added in Phase 0; limited writers.
- `users.is_active` added; no admin UI to deactivate.
- Stock qty still denormalized on `products.stock_qty` plus ledger.

## Technical debt

- Large controllers; mixed flash of `ValueError` text.
- Duplicate vendor templates (`vendor_form.html` vs add/edit).
- Employee module thinner than other masters.

## Security gaps (after Phase 0)

Addressed: CSRF on POST, POST cancels, session cookies httponly/samesite, idle timeout, login lockout, open-redirect guard, `FLASK_DEBUG` default off, `SECRET_KEY` warning, password hashing, audit on auth/cancel.

Remaining: no RBAC, default SECRET in DDEV only, brute-force is in-memory (not shared across workers), file-upload review incomplete, IDOR not systematically tested.

## UI/UX gaps

Shell is consistent. Missing: global search, breadcrumbs, notifications bell, collapsed sidebar tooltips, company settings screens.

## Testing gaps

- Unit tests for document totals and `safe_next` (Phase 0).
- No integration tests for stock/payment/cancel.
- No UI/e2e tests.

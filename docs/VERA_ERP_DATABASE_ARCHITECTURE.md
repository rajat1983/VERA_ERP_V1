# VERA ERP — database notes

MariaDB 10.11 via DDEV. Connection: `db.py` (`host=db`, database `vera_erp`). Parameterized PyMySQL.

## Core tables (observed / ensured)

- `customers`, `vendors`, `products`, employees table used by employee module
- `sales`, sale items, `purchases`, purchase items
- `stock_movements` (ledger)
- `payments` (customer receipts)
- `production_batches`
- `company` (invoice header)
- `users` (`password_hash`, `is_active`)
- `audit_log` (Phase 0)

Schema bootstrap: `utils/schema.py` `ensure_schema()` — additive ALTERs only.

## Integrity rules

- Invoice numbers allocated under `GET_LOCK`.
- Status columns widened to VARCHAR(20) to store `cancelled` (MySQL 1265).
- Stock quantity on `products.stock_qty` must stay in sync with movement writers.

Rollback of `ensure_schema`: drop added columns/tables only after backup; do not run casually in production.

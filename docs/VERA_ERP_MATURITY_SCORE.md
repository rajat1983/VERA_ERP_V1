# VERA ERP — maturity score

Scoring method: master prompt V2, 12 dimensions, 1–10, not inflated.
Date: 23 Aug 2026 after implementing Phases 0–10 to the extent the current schema allows (no invented BOM or CGST/SGST).

| Dimension | Score | Notes |
| --- | ---: | --- |
| Functionality | 7.5 | Adjustments, AP receipts, aging, company settings |
| UI/UX | 7.5 | Shared shell plus inventory/settings screens |
| Business logic | 7.5 | Sales/purchase GST and % discount unchanged |
| Data integrity | 7.0 | Transactions; stock qty still denormalized |
| Inventory | 7.5 | On-hand, low, movements, audited adjustments |
| Financial | 7.0 | AR + AP receipts and aging |
| Security | 6.5 | Admin role on settings/wipe; default admin remains |
| Accessibility | 6.5 | Focus rings, chart tables, Tippy keyboard |
| Performance | 6.0 | Unmeasured |
| Testing | 3.5 | Totals unit tests only |
| Maintainability | 6.0 | Nested python-mysql-ddev copy remains |
| Production readiness | 5.5 | healthz, .env.example, logging; no hosted backup job |

**Overall (mean): 6.5 / 10**

World-class bar remains 8.5+. Missing: full RBAC, integration tests, BOM, GSTR, hosted backups.

## Prompt phase map

| Phase | State |
| --- | --- |
| 0 Audit | Done |
| 1 Design system and shell | Done |
| 2 Master data | CRUD done; 360/credit still thin |
| 3 Sales | Done for agreed rules |
| 4 Purchase | Done; vendor pay now exists |
| 5 Inventory | On-hand, low, adjust, ledger |
| 6 Invoice and payments | Invoice + AR + AP |
| 7 Production | Batch create/cancel only (no BOM) |
| 8 Reports and dashboard | CSV, aging, payables on dashboard |
| 9 Security / a11y | Admin role, CSRF, sessions; not WCAG certified |
| 10 Production readiness | healthz and env template; deploy is still DDEV |

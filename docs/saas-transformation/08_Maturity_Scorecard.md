# 08 — Maturity Scorecard

**Scale:** 0 not implemented … 5 commercial/production ready.  
**Rule:** no points for Coming Soon, unused `routes/*.py`, or the nested `python-mysql-ddev` app.  
**Date:** 24 Nov 2026. Evidence: source review (MariaDB not dumped).

## Scoring method

Category scores are 0–5. Overall is a **weighted** mean converted to percent of 5.

| Category | Weight | Why |
|---|---:|---|
| SaaS readiness | 22% | This blueprint’s goal |
| Security | 18% | Shared platform blast radius |
| Business logic | 16% | Wrong money × N shops |
| Functional (ERP) | 14% | What tenants receive |
| Database | 12% | Isolation depends on schema |
| Technical architecture | 10% | Operability |
| UI/UX | 8% | Shop UX is ahead of platform UX |

## Category scores (current product)

| Category | Score /5 | Evidence |
|---|---:|---|
| Functional (ERP) | 2.9 | Sales/purchase/stock/POS/AR/AP exist; GL/expenses/returns/GSTR absent |
| Business logic | 2.8 | GST on pre-discount (`utils/totals.py`); POS not in `sales` reports; `stock_qty` editable |
| Security | 2.6 | CSRF POST + hashed passwords; GET deletes, seeds, XSS |
| UI/UX | 3.2 | Shared shell; add/edit inconsistency; no platform UI |
| Database | 2.0 | Incomplete bootstrap; no tenant keys; unique keys global |
| Technical architecture | 2.4 | One Flask app, DDEV, no CI, per-call DB connect, nested duplicate |
| **SaaS readiness** | **0.4** | No tenants, plans, payments, Super Admin, isolation, or expiry gate |

**Overall:**  
`(2.9×14 + 2.8×16 + 2.6×18 + 3.2×8 + 2.0×12 + 2.4×10 + 0.4×22) / 100`  
= `(40.6 + 44.8 + 46.8 + 25.6 + 24.0 + 24.0 + 8.8) / 100`  
= **2.15 / 5 → 43% commercial SaaS readiness**

(The earlier internal-tool score ~52% used a lower SaaS weight. For **selling subscriptions**, SaaS readiness dominates — hence 43%.)

## Existing module-wise maturity (ERP as a single shop)

| Module | Score | Status |
|---|---:|---|
| Sales | 4.0 | Advanced SME |
| Inventory | 3.5 | Functional+ |
| Purchases | 3.5 | Functional+ |
| Products | 3.5 | Functional+ (delete broken) |
| Payments AR/AP | 3.5 | Functional+ |
| Auth (shop) | 3.5 | Functional+ |
| Dashboard | 3.0 | Functional |
| POS | 3.0 | Functional, isolated ledger |
| Reports | 3.0 | Functional |
| Users/roles | 3.0 | Functional, hardcoded |
| Services | 3.0 | Functional POS catalog |
| Customers | 2.5 | Basic master |
| Company settings | 2.5 | Basic LIMIT 1 |
| Employees | 2.0 | Basic |
| Production | 2.0 | Basic |
| Shop admin wipe | 2.0 | Dangerous for SaaS |
| GenAI | 1.5 | Initial |
| Branches | 0 | Missing |
| Tenants | 0 | Missing |
| Subscriptions | 0 | Missing |
| Super Admin | 0 | Missing (`/admin` is shop wipe) |
| Accounting GL | 0 | Missing |
| Expenses | 0 | Missing |
| Platform billing | 0 | Missing |

## Target after Phases 1–3 (architecture + Super Admin + billing)

Not scored as done — **plan only**. Expected band if executed as specified: SaaS readiness **3.0**, overall **~3.2 / 5 (64%)** — sellable to first shops with isolation tests green. Phase 4 (tenantize ERP) is what actually moves isolation from design to production.

## Target after Phase 6

SaaS readiness **4.0+**, overall **~4.0 / 5 (80%)** — commercial MVP (still no GL/branches unless Phase 5 is in). World-class 5.0 needs GL, GSTR, WCAG, dedicated isolation options.

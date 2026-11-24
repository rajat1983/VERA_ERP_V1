# 09 — Implementation Roadmap

**Do not start coding until this document is approved.** Estimates are **person-weeks** for one senior engineer familiar with this repo (add 30–50% if parallelized poorly).

### Development Roadmap

| Phase | Deliverables | Dependencies | Estimated Effort |
|---|---|---|---|
| **0 Audit** | This folder (`docs/saas-transformation/`) | Source tree | **Done** |
| **1 SaaS architecture & tenant foundation** | `tenants` table; `g.tenant_id`; migration plan for `tenant_id` on all business tables; `utils/tenant.py`; login shop-code field (can sit behind flag); two-tenant isolation tests; kill `ensure_default_admin` seeds; require `SECRET_KEY` | Phase 0 | **3–4 weeks** |
| **2 Super Admin & shop onboarding** | `/platform/login`, dashboard, shop list, shop create; public `/signup`; provision shop_admin user; split platform vs shop roles; neutralize `/admin` reset as global wipe | Phase 1 tenant row | **2–3 weeks** |
| **3 Subscription & billing** | Plans CRUD 3/6/9/12; Razorpay + webhook; platform invoices; status machine; `_guard` expiry allowlist; `/billing/expired`; reminders cron; manual activate/extend | Phase 2 tenants | **3–4 weeks** |
| **4 Existing ERP tenantization** | Thread `tenant_id` through every model listed in `02_`; unique indexes; IDOR 404s; POS in sales numbers; product delete POST + `can_delete_product`; stop product-form stock overwrite; GET deletes gone; XSS escape | Phases 1–3 | **6–8 weeks** |
| **5 Commercial features** | Entitlements (POS/production flags); user seat limits; trial/coupons; branch_id UI optional; shop CSV export; support mailbox process | Phase 4 stable | **4–6 weeks** |
| **6 Quality, security, production** | Isolation + payment + expiry test matrix; CSRF/upload/lockout hardening; HTTPS Secure cookie; backups; monitoring; pagination; pin deps; CI; legal pages; load test | Phases 3–5 | **3–4 weeks** |

**Calendar (serial):** ~22–29 weeks (~6–7 months).  
**With 2 engineers after Phase 1:** ~4.5–6 months (Phase 4 is the critical path).

## Phase 1 detail (first implementation slice — when approved)

1. Versioned SQL migrations (stop relying on `ensure_schema` alone).
2. `tenants` + backfill tenant 1 from `company`.
3. Add `tenant_id` to `users` and login resolution.
4. Helper `current_tenant_id()` used by **one** vertical (products) as the pattern.
5. Isolation test: tenant 1 product invisible to tenant 2 session.
6. Remove default passwords.

Do **not** start Razorpay or Super Admin UI before tenant_id exists on users and at least one master.

## Phase 4 module order (inside ERP)

1. Users + company settings  
2. Products, categories, services  
3. Customers, vendors  
4. Inventory  
5. Sales + payments  
6. POS (then wire reports)  
7. Purchases + vendor payments  
8. Production  
9. Dashboard + reports  
10. Employees / GenAI (or disable GenAI)

## Dependencies / risks

| Risk | Mitigation |
|---|---|
| Missed query without `tenant_id` | Central helper + grep CI + two-tenant tests |
| POS still omitted from reports | Phase 4 explicit story: union or posting |
| Unique SKU/username conflicts on backfill | Only one existing shop |
| Razorpay webhook vs CSRF `_guard` | Exempt webhook path with signature check, not CSRF cookie |
| Cron missing on DDEV | Document `.ddev` cron; production systemd |
| Dual app `python-mysql-ddev` | Do not migrate; archive |
| Scope creep GL/GSTR | Keep out of Phases 1–4 |

## MVP vs later (commercial)

**MVP (sell first subscriptions):** shared DB, Super Admin, signup, plans, Razorpay, expiry lock, tenantized existing ERP, isolation tests, backups, legal pages.

**Not MVP:** branches UI, coupons, GL, expenses, CRM pipeline, GSTR, subdomain tenancy, dedicated DB, impersonation, in-app tickets, GenAI.

## Suggested first PR after approval

“Phase 1a: tenants table, session tenant_id, users scoped, isolation test, remove seed passwords.” Small enough to review; unblocks everything else.

# 03 — New Module Requirements

Shop ERP screens already exist. SaaS needs a **platform product** beside them. Implement in the sequence in `09_Implementation_Roadmap.md`.

### New Module Development

| Module | Purpose | Key Features | Dependencies | Priority |
|---|---|---|---|---|
| Super Admin Dashboard | Platform operator home | Shop counts (active/expired/suspended/pending), MRR/collected, expiring in 7/15/30 days, failed payments, recent signups | Tenants, subscriptions, platform payments | P2 |
| Shop / business registration | Public or invite signup | Shop name, GSTIN, owner email, password, tenant slug; email verify; status Pending until pay or trial | Tenants, mailer, unique slug | P2 |
| Tenant management | Super Admin CRUD for shops | View/suspend/reactivate shop; owner contacts; notes; **no** cross-shop data browser of invoices in MVP (privacy) | Tenants, users | P2 |
| Subscription plan management | Configurable plans | Duration 3/6/9/12 months (and custom); price, GST, currency INR; max users; feature flags; active/hidden | `subscription_plans` | P3 |
| Subscription management | Lifecycle per shop | Status Pending/Active/Grace/Expired/Suspended/Cancelled; start/end; grace days; manual extend/activate | Plans, tenants | P3 |
| Payment gateway | Collect plan fees | Razorpay orders (India), webhook signature verify, idempotent capture | Gateway keys in platform settings | P3 |
| Platform billing invoices | Tax-compliant SaaS invoices | Sequential platform invoice, GST break-up, PDF, shop billing GSTIN | Payments, company (platform) GSTIN | P3 |
| Renewal & expiry | Keep shops paying | Dunning, reminders T-15/T-7/T-1, grace, lock ERP, renewal checkout | Scheduler (cron), mailer, SMS optional later | P3 |
| Notification management | Templates | Email templates for signup, activate, expiry, payment fail; Super Admin broadcast (opt-in later) | mailer.py | P3 |
| Platform reports | Operator analytics | New shops, churn, revenue, plan mix, failed payments — **not** shop P&L | Aggregates only | P3 |
| Feature access / entitlements | Plan gates | e.g. POS, production, extra users, extra branches | Plans, middleware | P5 |
| Platform audit & monitoring | Trust | Super Admin actions, login, payment webhooks, isolation test log | `audit_log` + metrics | P6 |
| Tenant provisioning | Create isolated workspace | Seed shop roles, default units/categories optional, copy empty schema | Schema, tenant row | P2 |
| Subscription enforcement middleware | Block expired shops | After auth: if shop expired and path not in allowlist → `/billing/expired` | Session tenant, subscription | P3 |
| Support / tickets (minimal) | Commercial ops | Shop submits issue; Super Admin list/reply. Can be email-only in MVP | mailer | P5 (MVP: email) |
| Legal pages | Compliance | Terms, privacy, refund — static, Super Admin editable later | Settings | P6 |
| Backup / export | Shop data pack | Super Admin export one tenant SQL/CSV; shop self-export P5 | tenant_id everywhere | P6 |

## Additional modules required to operate commercially (not optional forever)

| Module | MVP? | Note |
|---|---|---|
| Platform settings | Yes | Razorpay keys, platform GSTIN, grace days default, support email |
| Cron / job runner | Yes | Reminders and expiry; DDEV cron or systemd. Flask request-cycle is not enough |
| Health beyond `/healthz` | Yes | DB ping; queue/cron heartbeat |
| Shop billing self-serve | Yes | Owner pays/renews without Super Admin |
| Coupon / trial | No (P5) | Trial 14 days; coupon % off first term |
| Branches | No (P5) | See architecture: bill at tenant, optional branch add-on |
| Accounting GL | No | Do not block SaaS launch |
| In-app support desk | No | Email + WhatsApp process first |

## Super Admin vs shop admin (naming)

Today `session["role"] == "admin"` is the **shop** owner (`utils/permissions.py`). For SaaS:

| Actor | Stored as | UI |
|---|---|---|
| Platform operator | `platform_users.role = super_admin` (separate table) | Super Admin panel `/platform/*` |
| Shop owner | `users.shop_role = shop_admin` | Existing ERP, `/settings` |
| Shop manager / staff | existing manager/staff | Existing ERP |

**Never** reuse `/admin` wipe tools as the platform panel. New blueprint prefix: `/platform`.

## Screens (Super Admin) — functional spec summary

- `/platform/login` — separate login, not shop `/login`
- `/platform` — KPI dashboard
- `/platform/shops` — list/filter/status
- `/platform/shops/<id>` — profile, subscription, payments, users count (not invoice line items)
- `/platform/plans` — CRUD prices and durations
- `/platform/subscriptions` — activate, extend, suspend
- `/platform/payments` — gateway + manual
- `/platform/reports/revenue`
- `/platform/audit`
- `/platform/settings`

Shop owner (after expiry): `/billing/status`, `/billing/renew`, `/billing/invoices` only.

# 05 — Subscription Business Workflow

## Plans (configurable, not hardcoded)

Super Admin defines plans. Seed examples (prices illustrative only — **not** implemented):

| Code | Duration | Typical use |
| --- | --- | --- |
| Q3 | 3 months | Seasonal / trial commercial |
| Q6 | 6 months | Default starter |
| Q9 | 9 months | — |
| Q12 | 12 months | Best value |

Each plan row: name, duration_days, price_ex_gst, gst_rate, max_users, max_branches, feature JSON, is_public, is_active.

Shop never sees unpublished plans.

## Happy path

```
Shop registration
  → email verify (reuse activation_token pattern in users)
  → plan selection
  → Razorpay (or Super Admin “mark paid”)
  → subscription Active (starts_on, ends_on)
  → tenant status Active
  → ERP login allowed
  → T-15 / T-7 / T-1 reminder emails
  → renew (extend ends_on) or expire
```

## Status machine

| Status | ERP access | Notes |
| --- | --- | --- |
| Pending | No | Registered, unpaid / unverified |
| Active | Yes | `today <= ends_on` |
| Grace | Yes, banner | `ends_on < today <= ends_on + grace_days` |
| Expired | Billing only | Session ERP routes 402/redirect |
| Suspended | No | Super Admin or fraud / non-pay after grace |
| Cancelled | No | No auto-renew; data retained |

**Super Admin is never evaluated against a shop subscription.**

## Expiry enforcement (required)

On every request after login (`app.py` `_guard` extension):

1. If `platform_user` → continue.
2. Load subscription for `session.tenant_id` (cache in session with short TTL; re-check on billing webhooks).
3. If Active or Grace → continue (Grace sets flash/banner).
4. If Expired/Suspended/Cancelled/Pending:
   - Allow: `/logout`, `/billing/*`, `/profile` (password), static, healthz.
   - Deny: all ERP GET/POST including `/api/*`, `/pos/complete`, `/product-search`.
   - Render `templates/billing/expired.html` (renew CTA).
5. Invalidate “already logged in” ERP pages by running this **every request**, not only at login (existing idle timeout stays).

## Payments

- **Gateway (MVP):** Razorpay Orders + authorized webhooks (`X-Razorpay-Signature`).
- **Manual:** Super Admin records cheque/UPI and activates (needed for first customers).
- **Idempotency:** `gateway_payment_id` UNIQUE so double webhooks do not double-extend.
- **Failed payment:** status stays Active until `ends_on`; renewal attempt Failed → retry; after ends_on + grace → Expired.
- **Invoices:** platform tax invoice (not `payments` tied to `sale_id`). GST as per platform GSTIN and shop GSTIN (B2B).

## Renewal / change plan

- Renewal: new `subscription_events` row; if still Active, **extend** `ends_on` by plan duration from current `ends_on` (no lost days).
- Upgrade: charge prorated difference (P5). MVP: change plan at next renewal only.
- Downgrade: at renewal; if seats exceed new max_users, block until users deactivated.

## Notifications

Reuse `utils/mailer.py` with tenant-unaware SMTP. Templates:

- Registration received / verified
- Payment success + invoice
- Payment failed
- Expiry T-15, T-7, T-1
- Expired
- Manual extend by Super Admin

Cron (new): daily job `python -m jobs.subscriptions` — not request-driven.

## Grace period

Platform setting `default_grace_days` (e.g. 7), overridable per subscription. During grace: full ERP, persistent banner, no new year-long operations blocked.

## Shop-wise history

`subscriptions` (current) + `subscription_events` (every activate, pay, extend, suspend). Super Admin shop page lists events. Shop owner sees `/billing/history`.

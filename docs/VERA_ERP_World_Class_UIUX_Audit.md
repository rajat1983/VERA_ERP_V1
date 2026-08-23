# VERA ERP — World-Class UI/UX Audit

**Branch:** `VERA_ERP_V3`  
**Repository:** `rajat1983/VERA_ERP_V1`  
**Date:** 22 Aug 2026  
**Scope:** Flask + Jinja + Bootstrap 5 + existing JS (no new frontend framework)  
**Method:** Code inspection of `app.py`, `templates/`, `static/`, controllers, and known live routes. No fake data.

**Overall maturity: 4.8 / 10**

Business workflows (sales, purchase, stock, login) are usable. The product does not yet look or behave like one ERP. Navigation, layout, consistency, accessibility, and print/mobile are the largest gaps.

---

## 1. Executive Summary

VERA ERP is a working operational system: masters, sales, purchase, stock movements, payments, reports, and login exist. Several modules (vendor, product, dashboard) already use Bootstrap cards, search, and badges.

The experience is still a collection of screens, not a product:

- Global chrome is a rainbow button bar titled in the browser as VERA ERP but with no sidebar, breadcrumbs, page title region, or user menu.
- Sales/Purchase/Employee remain form-and-table pages; Product/Vendor/Dashboard are more finished. Daily users must re-learn each module.
- `base.html` loads customer, vendor, location, Chart.js, SweetAlert, Tippy, and employee live-search on **every** page.
- Login credentials are shown on the login screen (security UX).
- Debug-style errors can still reach the browser (`debug=True` unless env is set).
- Invoice print CSS hides `.btn` only, not the global nav.
- No design tokens beyond dashboard-specific CSS. Spacing, buttons, tables, and empty states are page-specific.

**Do not rewrite business logic.** Raise the shell, design system, and the highest-traffic workflows (Sales, Purchase, lists) to one pattern.

---

## 2. Current Strengths

- Bootstrap 5 + Bootstrap Icons already in place; no React/Vue needed.
- Tippy.js for sales product info (stock, cost, selling, GST) is the agreed pattern and is wired.
- Sales calculations match the business rules (qty × price, % discount, GST from `tax_rate`, server authoritative).
- Vendor/Customer/Product lists: search, pagination, status badges, icon actions.
- Dashboard has real KPIs, charts, low-stock, health — not demo data.
- SweetAlert used for sale/purchase confirmations.
- Flash messages exist globally.
- CSRF helper and session login exist.

---

## 3. Critical UX Problems (P0)

1. **No application shell.** Rainbow `btn-group` nav, nested `<a><button>`, no active state, no grouping, no mobile drawer.
2. **Inconsistent page language.** Product “management suite” vs Sales “Create Sale” heading vs Employee bare table.
3. **Scripts on every page.** Employee `autoSearch` and vendor/customer JS run globally; Chart.js on login.
4. **Login is not a focused auth screen.** It inherits the full ERP nav and shows default passwords.
5. **Print invoice still shows app chrome.**
6. **Unsafe error UX.** Tracebacks and `Error : {e}` flash strings.
7. **Employee live search can fail** if `#searchBox` is missing on other pages (`autoSearch` in `base.html`).
8. **No viewport meta** — mobile layout is accidental.

---

## 4. Module-by-Module Audit

### 4.1 Login / Authentication

| | |
|---|---|
| Works | Session login, CSRF, logout, default admin bootstrap |
| Incomplete | Password change, lockout, roles, “remember me”, branded auth layout |
| Broken / risk | Default password printed on screen; login uses full `base.html` nav |
| UI | Unstyled stacked fields |
| UX | After login, no home breadcrumb; next= works |
| A11y | Labels present; no `autocomplete` attributes |
| Responsive | Inherits container; no dedicated card |

### 4.2 Dashboard

| | |
|---|---|
| Works | KPIs, charts, alerts, low stock, recent txns, date filter for sales chart |
| Incomplete | Receivables/payables as first-class tiles; filter does not apply to all KPIs |
| UI | Strongest visual module; emoji KPI icons; “Welcome back, Rajat” hardcoded |
| UX | Not a command center: weak “what should I do next?” |
| A11y | Charts need text equivalents; emoji as icons |

### 4.3 Employee

| | |
|---|---|
| Works | CRUD, pagination, search |
| Incomplete | Role, phone, status; empty state |
| UI | Oldest pattern (`h3` + bordered table) |
| UX | Live search in layout is employee-specific and fragile |
| Actions | Text Edit/Delete, not icon row |

### 4.4 Customer / Vendor

| | |
|---|---|
| Works | Full CRUD, GST, search, pagination, view |
| Incomplete | Bulk actions, saved filters, sort headers |
| UI | Closest to a list standard; Action column was wrapping (vendors fixed) |
| Empty | Copy exists on vendor; not identical on all masters |

### 4.5 Product

| | |
|---|---|
| Works | Image, vendor, prices, stock, reorder, tax/HSN/unit/type on add/edit |
| Incomplete | List does not highlight tax/HSN; no last purchase/sale on view |
| UI | Best master form (two-column card) |
| UX | Vendor autocomplete vs sales dropdown — two interaction models |

### 4.6 Purchase

| | |
|---|---|
| Works | Vendor, lines, discount, GST, cancel+stock reverse, pagination |
| Incomplete | Visual parity with Sales; remarks; `-- Select Vendor --` wording |
| UI | Flat table, “X” remove, mixed FA vs Bootstrap icons on view |
| UX | Not the same section model as Sales (header / items / totals) |

### 4.7 Sales (high priority)

| | |
|---|---|
| Works | Dropdowns, today date, Tippy, discount %, GST, save confirm, cancel stock |
| Incomplete | Sectioned layout; Save & Print; invoice header branding on create |
| UI | Raw labels, no card wrapping; financial summary exists |
| UX | Workflow is correct but not visually sequenced; edit label said ₹ then corrected to % |
| Preserve | `-- Select Customer --` / `-- Select Product --`; Tippy; remarks + discount above grand total |

### 4.8 Production

| | |
|---|---|
| Works | Create batch, list, cancel |
| Incomplete | BOM visibility, history detail, empty recipes UX |
| UI | Minimal add form |

### 4.9 Inventory / Stock

| | |
|---|---|
| Works | Movement list with search |
| Incomplete | Stock-on-hand workspace (available / reorder / value); “Stock” vs movements naming |
| UX | Qty sign (+/−) not explained |

### 4.10 Invoice

| | |
|---|---|
| Works | Company block, items, discount, GST, words, payment badge, print button |
| Incomplete | Hide shell on print; PDF; consistent GST column on lines |
| Broken | Invalid HTML `div "padding:10px 15px"` |

### 4.11 Payments / Reports / Admin

| | |
|---|---|
| Payments | Functional record form; dense; no due-aging view |
| Reports | Index + generic table; no export; filters only dates |
| Admin | Dangerous reset/clear; not in nav; no confirm pattern on all actions |

### 4.12 Global navigation / JS / errors

- Nav: colored buttons, duplicate primary colors (Dashboard and Products both green), no `aria-current`.
- JS: `common.js` + module files + layout inline employee search.
- Errors: Flask debug; flashed exception text.

---

## 5. Maturity Score (1–10)

| Module | Func | UI | UX | Consist. | A11y | Resp. | Perf | Prod-ready | Avg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Login | 6 | 3 | 4 | 3 | 3 | 4 | 7 | 4 | 4.3 |
| Dashboard | 7 | 6 | 5 | 4 | 3 | 5 | 6 | 5 | 5.1 |
| Employee | 5 | 3 | 4 | 3 | 3 | 4 | 6 | 4 | 4.0 |
| Customer | 7 | 6 | 6 | 5 | 4 | 5 | 6 | 6 | 5.6 |
| Vendor | 7 | 6 | 6 | 5 | 4 | 5 | 6 | 6 | 5.6 |
| Product | 7 | 7 | 6 | 5 | 4 | 5 | 6 | 6 | 5.8 |
| Purchase | 6 | 4 | 5 | 4 | 3 | 4 | 6 | 5 | 4.6 |
| Sales | 7 | 4 | 6 | 4 | 4 | 4 | 6 | 6 | 5.1 |
| Production | 5 | 3 | 4 | 3 | 3 | 4 | 6 | 4 | 4.0 |
| Inventory | 5 | 4 | 4 | 4 | 3 | 4 | 7 | 5 | 4.5 |
| Invoice | 6 | 5 | 5 | 4 | 3 | 3 | 6 | 5 | 4.6 |
| Payments | 5 | 4 | 4 | 4 | 3 | 4 | 7 | 4 | 4.4 |
| Reports | 5 | 4 | 4 | 4 | 3 | 4 | 7 | 4 | 4.4 |
| Admin | 3 | 2 | 2 | 2 | 2 | 3 | 5 | 2 | 2.6 |
| App shell / nav | 4 | 2 | 2 | 2 | 2 | 3 | 6 | 3 | 3.0 |

**Strongest:** Product, Customer, Vendor, Dashboard (data), Sales (logic).  
**Weakest:** App shell, Admin, Employee, Production, Login presentation.

---

## 6. Design System Recommendation

There is **no** real design system today. `vera-dashboard.css` is dashboard-only (shadows, KPI cards).

Create `static/css/vera-theme.css` with CSS variables only (no new framework):

| Token | Recommendation |
|---|---|
| Font | System UI / “Segoe UI”, Roboto, sans-serif — tabular nums for money |
| Primary | One blue (`#1d4ed8`) for nav + primary buttons |
| Success / warning / danger | Bootstrap semantic mapped to tokens |
| Surface | `#fff` cards on `#f4f7fb` background (already used) |
| Radius | 8px controls, 12px cards |
| Space | 4/8/12/16/24/32 |
| Buttons | `btn-primary` / `btn-outline-secondary` / `btn-danger` only; stop rainbow nav |
| Tables | `table align-middle`, numeric `text-end`, `text-nowrap` actions |
| Page header | Title + subtitle + primary action row |

Reuse: `page-header`, `data-table`, `form-section`, `totals-panel`, `empty-state`.

---

## 7. Navigation Recommendation

Replace the button bar with a **left sidebar** (collapse on desktop, offcanvas on mobile).

Proposed IA (mapped to existing routes):

```text
Dashboard                         /dashboard

Masters
  Customers                       /customers
  Vendors                         /vendors
  Products                        /products
  Employees                       /list

Transactions
  Sales                           /sales
  Purchases                       /purchases
  Production                      /production
  Payments                        /payments

Inventory
  Stock movements                 /stock-movements

Documents
  (Sales invoice via sale view)

Reports                           /reports

Account
  Logout                          /logout
```

Top bar: page title (block), user name, no fake notifications until they exist.

Active item: match `request.path`.

---

## 8. Dashboard Recommendation

Keep real queries. Evolve toward a command center:

- Row 1: Today sales, month sales, stock value, low stock count, unpaid invoices.
- Row 2: Sales trend (existing chart + date filter applied to KPIs too).
- Row 3: Action lists — low stock, pending payments, recent sales/purchases.
- Remove hardcoded “Rajat” and emoji as the only iconography (use Bootstrap Icons).

---

## 9. Sales Recommendation

Keep dropdowns and Tippy. Restructure **layout only**:

1. Card: Customer + date + invoice meta  
2. Card: Items table, Add Item, Tippy  
3. Row: Remarks + Discount | Totals (subtotal, discount amt, GST, grand)  
4. Sticky footer actions: Save, Cancel  

Optional P2: Save & Print after successful save redirect to view.

---

## 10. Purchase Recommendation

Mirror Sales section structure, same tokens, `-- Select Vendor --`, Bootstrap Icons for remove, totals panel identical.

---

## 11. Inventory Recommendation

Keep movements table. Add a simple stock-on-hand report already at `/reports/stock` into Inventory group. Explain signed quantities (in/out) with badges.

---

## 12. Invoice Recommendation

- `@media print { .app-shell { display:none } }`
- Fix invalid padding div  
- Show line GST if needed; payment status already present  
- Amount in words keep `num2words`

---

## 13. Responsive / Mobile

Add `viewport`. Sidebar → offcanvas. Tables → `table-responsive`. Primary actions remain visible. Totals stack under items (already col-md). Touch targets ≥ 40px for icon buttons.

Breakpoints to verify: 1920, 1366, 768, 390.

---

## 14. Accessibility (WCAG 2.2 AA direction)

- `html lang="en"`
- Visible focus rings
- Labels `for`/`id` on sales create
- Nav `aria-label`, `aria-current="page"`
- Status not color-only (badge text already helps)
- Tippy: keyboard access to product info
- Don’t use `confirm()` only; keep SweetAlert with focus trap where used

---

## 15. Performance

- Split layout JS: load `customer.js` / `vendor.js` / Chart.js only on those pages.
- Remove employee `autoSearch` from `base.html`; keep in employee template.
- Tippy/Popper only on sales add/edit.
- Product images: already local; add max dimensions in CSS.

---

## 16. Security UX

- Never show `admin123` on login in production; env-flag the hint.
- `FLASK_DEBUG=0` in production; generic flash on unexpected errors.
- Admin reset only for authenticated users (already behind login) + strong confirm; do not link in main nav until roles exist.
- Hiding nav is not authorization (already server session).

---

## 17. Pattern matrix

| Pattern | Current state | Problem | Recommendation | Priority |
|---|---|---|---|---|
| Navigation | Rainbow buttons | No IA, no active state, invalid nested buttons | Sidebar + groups + aria | P0 |
| Dashboard | KPI cards + charts | Hardcoded name, emoji, filter scope | Command center + icons | P1 |
| Page header | Inconsistent | Every module different | Shared `page-header` | P0 |
| Breadcrumb | None | No orientation | Optional under title | P2 |
| Buttons | Many colors | Meaningless color coding | Semantic only | P0 |
| Forms | Mixed | Sales unlabeled grouping | Section cards | P1 |
| Tables | Mixed | Wrap actions, no numeric align | nowrap actions, `text-end` money | P1 |
| Search | Per page | OK on masters, weak on sales | Keep simple search + reset | P2 |
| Filters | Sparse | Dashboard dates only | Date on reports (exists) | P2 |
| Validation | Mixed HTML5 / flash | Inconsistent | Server flash + field errors | P1 |
| Notifications | Bootstrap alerts | OK | Keep; no toasts required | P2 |
| Empty states | Some lists | Missing on employee/sales | Standard empty + CTA | P1 |
| Loading | None | Search feels instant or broken | Optional spinner on live search | P2 |
| Modals | Employee unused vs routes | Dead modal in template | Remove or wire | P2 |
| Tooltips | Tippy on sales | Not keyboard | Tab-accessible info | P1 |
| Responsive | No viewport | Mobile unusable chrome | Viewport + offcanvas | P0 |
| Accessibility | Weak | Contrast/nav/labels | AA pass on shell + sales | P1 |
| Print | Partial | Nav prints | Hide `.app-shell` | P0 |

---

## 18. Prioritized roadmap

### P0 — Critical (Phase 1)

- Design tokens CSS  
- App shell: sidebar, main, viewport, `lang`  
- Auth layout without ERP nav; hide default password unless `VERA_SHOW_DEFAULT_LOGIN=1`  
- Print: hide shell  
- Move page-specific JS out of `base.html`  
- Fix invoice invalid HTML  

### P1 — High (Phases 2–5)

- Dashboard command-center cleanup  
- Shared list header + empty states  
- Sales and Purchase section layout (no business-rule change)  
- Sticky numeric totals, action nowrap everywhere  
- Generic error flash (no raw exceptions)  

### P2 — Medium

- Breadcrumbs, global search, Save & Print  
- Stock-on-hand landing  
- Report export  
- Employee fields parity  

### P3 — Later

- Dark mode, bulk actions, PDF engine, role UI, notifications inbox  

### Implementation sequence

1. Theme + shell + login + print + JS split  
2. Dashboard polish  
3. Master list pattern (employee catch-up)  
4. Purchase = Sales visual system  
5. Sales layout  
6. Inventory copy/badges  
7. Invoice print QA  
8. Reports/payments/production headers  
9. Responsive + a11y sweep  
10. QA  

**Estimated complexity:** Phase 1–2: 1–2 days. Phases 3–5: 2–4 days. Full P0–P1: about one week of focused UI work without touching GST/stock rules.

---

## 19. Acceptance criteria (Phase 1)

- All current routes still work.  
- Sales dropdowns and Tippy unchanged in behavior.  
- One primary nav, active link, works at 390px.  
- Login has no full ERP menu.  
- Printed invoice has no sidebar/buttons.  
- Browser console: no `searchBox` null errors on non-employee pages.

---

## 20. What this audit will not change

- Sales customer/product **dropdowns** (no autocomplete).  
- Discount as **percent**.  
- Server-side totals.  
- Tippy content fields.  
- Flask/Jinja architecture.

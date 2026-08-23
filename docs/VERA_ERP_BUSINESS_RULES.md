# VERA ERP — business rules (confirmed)

Do not invent tax splits or autocomplete on sales.

## Sales

- Customer and product are **dropdowns only**. Placeholder: `-- Select Customer --` / `-- Select Product --`.
- No autocomplete. No customer/product **code** on Add Sale.
- Tippy on product: available stock, purchase price, selling price, GST %.
- `line_amount = qty × price`
- `subtotal = sum(line_amount)`
- Discount is **percent** 0–100: `discount_amount = subtotal × % / 100`
- GST from each product `tax_rate` on the line amount. **No CGST/SGST/IGST columns.**
- `grand_total = subtotal − discount_amount + GST`
- Server totals are authoritative (`utils.totals.calculate_document_totals`).
- Stock deducted on confirm; cancel restores stock and writes a reversal movement.
- Invoice numbers unique per year with `GET_LOCK`.

## Purchase

- Same GST/discount model as sales.
- Purchase increases stock; cancel reverses stock.

## Payments

- Against confirmed sales invoices only.
- Amount cannot exceed remaining outstanding unless a future rule explicitly allows overpayment (not enabled).

## Production

- Finished-goods batch increases stock; cancel reverses that batch.
- BOM consumption is **out of scope** until product requirements justify it.

## Auth

- Inactive users (`users.is_active = 0`) cannot authenticate.
- CSRF required on POST when `VERA_AUTH=1`.
- Failed logins lock that IP+username for 15 minutes after 5 failures (process-local).

# VERA ERP — test plan

## Automated (Phase 0)

```bash
pytest tests/test_totals.py
```

Covers: line amount, GST from `tax_rate`, discount 0/10/100, discount >100 rejected, `safe_next`.

## Sales matrix (manual until integration tests exist)

- One / multiple products, add/remove row, product change
- Qty zero/negative, qty > stock, exact stock
- Discount 0 / 10 / 100 / >100
- Save, failed save, edit qty up/down, cancel, cancel twice
- Invoice print, payment not above outstanding

## Purchase / inventory (manual)

- Stock in on purchase, reverse on cancel
- Production in / cancel reverse
- Negative stock attempt on sale

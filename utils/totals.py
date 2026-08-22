def calculate_document_totals(items, discount_percent):
    """GST uses each product tax_rate. No CGST/SGST split (not in schema)."""
    subtotal = 0.0
    gst_amount = 0.0

    for item in items:
        qty = float(item["qty"])
        price = float(item["price"])
        tax_rate = float(item.get("tax_rate") or 0)
        line_amount = qty * price
        item["line_total"] = round(line_amount, 2)
        item["line_gst"] = round(line_amount * tax_rate / 100.0, 2)
        subtotal += line_amount
        gst_amount += item["line_gst"]

    discount_percent = float(discount_percent or 0)
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0% and 100%.")

    discount_amount = round(subtotal * discount_percent / 100.0, 2)
    grand_total = round(subtotal - discount_amount + gst_amount, 2)
    if grand_total < 0:
        raise ValueError("Grand total cannot be negative.")

    return {
        "subtotal": round(subtotal, 2),
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "gst_amount": round(gst_amount, 2),
        "grand_total": grand_total,
    }

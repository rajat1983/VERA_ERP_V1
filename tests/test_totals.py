import pytest

from utils.totals import calculate_document_totals


def test_line_and_gst_percent_discount():
    items = [
        {"qty": 2, "price": 100, "tax_rate": 18},
        {"qty": 1, "price": 50, "tax_rate": 5},
    ]
    totals = calculate_document_totals(items, 10)
    assert items[0]["line_total"] == 200.0
    assert items[0]["line_gst"] == 36.0
    assert items[1]["line_total"] == 50.0
    assert items[1]["line_gst"] == 2.5
    assert totals["subtotal"] == 250.0
    assert totals["discount_amount"] == 25.0
    assert totals["gst_amount"] == 38.5
    assert totals["grand_total"] == 263.5


def test_discount_zero_and_hundred():
    items = [{"qty": 1, "price": 200, "tax_rate": 0}]
    zero = calculate_document_totals(list(items), 0)
    assert zero["discount_amount"] == 0
    assert zero["grand_total"] == 200
    full = calculate_document_totals([{"qty": 1, "price": 200, "tax_rate": 10}], 100)
    assert full["discount_amount"] == 200
    assert full["grand_total"] == 20


def test_discount_out_of_range():
    items = [{"qty": 1, "price": 10, "tax_rate": 0}]
    with pytest.raises(ValueError):
        calculate_document_totals(items, 101)
    with pytest.raises(ValueError):
        calculate_document_totals(items, -1)


def test_safe_next():
    from utils.auth import safe_next
    assert safe_next("/sales") == "/sales"
    assert safe_next("//evil.example") == "/dashboard"
    assert safe_next("https://evil.example") == "/dashboard"
    assert safe_next(None, "/dashboard") == "/dashboard"

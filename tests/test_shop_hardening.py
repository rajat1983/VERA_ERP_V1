import inspect

from controllers import customer_controller, employee_controller, product_controller, sales_controller, vendor_controller


def test_master_delete_routes_are_post_only():
    sources = [
        inspect.getsource(product_controller.delete),
        inspect.getsource(customer_controller.delete),
        inspect.getsource(vendor_controller.delete_vendor),
        inspect.getsource(employee_controller.delete),
    ]
    for source in sources:
        assert 'methods=["POST"]' in source or "methods=['POST']" in source


def test_sale_view_uses_abort():
    source = inspect.getsource(sales_controller.sale_view)
    assert "abort(404)" in source

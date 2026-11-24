from utils.tenant import tid


def require_product(cur, product_id, for_update=True):
    sql = "SELECT * FROM products WHERE id=%s AND tenant_id=%s"
    if for_update:
        sql += " FOR UPDATE"
    cur.execute(sql, (product_id, tid()))
    row = cur.fetchone()
    if not row:
        raise ValueError("Product not found.")
    return row


def require_vendor(cur, vendor_id, for_update=True):
    sql = "SELECT id FROM vendors WHERE id=%s AND tenant_id=%s"
    if for_update:
        sql += " FOR UPDATE"
    cur.execute(sql, (vendor_id, tid()))
    row = cur.fetchone()
    if not row:
        raise ValueError("Vendor not found.")
    return row


def require_customer(cur, customer_id, for_update=False):
    sql = "SELECT id FROM customers WHERE id=%s AND tenant_id=%s"
    if for_update:
        sql += " FOR UPDATE"
    cur.execute(sql, (customer_id, tid()))
    row = cur.fetchone()
    if not row:
        raise ValueError("Customer not found.")
    return row


def bump_stock(cur, product_id, delta, allow_negative=False):
    tenant_id = tid()
    if delta >= 0:
        cur.execute(
            "UPDATE products SET stock_qty = stock_qty + %s WHERE id=%s AND tenant_id=%s",
            (delta, product_id, tenant_id),
        )
        if cur.rowcount == 0:
            raise ValueError("Product not found.")
        return
    qty = -delta
    if allow_negative:
        cur.execute(
            "UPDATE products SET stock_qty = stock_qty - %s WHERE id=%s AND tenant_id=%s",
            (qty, product_id, tenant_id),
        )
        if cur.rowcount == 0:
            raise ValueError("Product not found.")
        return
    cur.execute(
        """
        UPDATE products
        SET stock_qty = stock_qty - %s
        WHERE id=%s AND tenant_id=%s AND stock_qty >= %s
        """,
        (qty, product_id, tenant_id, qty),
    )
    if cur.rowcount == 0:
        raise ValueError("Cannot update stock for this product.")


def record_movement(cur, product_id, movement_type, quantity, reference_id, reference_type, remarks=None):
    cur.execute(
        """
        INSERT INTO stock_movements
            (tenant_id, product_id, movement_type, quantity, reference_id, reference_type, remarks)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (tid(), product_id, movement_type, quantity, reference_id, reference_type, remarks),
    )

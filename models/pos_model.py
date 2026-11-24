from datetime import date, datetime

from db import get_db_connection
from models import service_model
from utils.tenant import tid
from utils.totals import calculate_document_totals


def _num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def catalog(kind="product", category="", search=""):
    kind = (kind or "product").lower()
    if kind == "service":
        rows = service_model.active_catalog(search, category)
        items = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "sku": row.get("category") or "",
                    "image": "",
                    "price": _num(row["price"]),
                    "stock_qty": 99999,
                    "tax_rate": 0,
                    "unit": row["unit"] or "page",
                    "category": row.get("category") or "",
                    "product_type": "service",
                }
            )
        return items
    conn = get_db_connection()
    cur = conn.cursor()
    where = ["p.tenant_id=%s", "LOWER(IFNULL(p.status, 'active')) = 'active'"]
    params = [tid()]
    where.append("LOWER(IFNULL(p.product_type, 'finished_goods')) <> 'raw_material'")
    where.append("LOWER(IFNULL(p.product_type, 'finished_goods')) <> 'service'")
    if category:
        where.append("p.category = %s")
        params.append(category)
    search = (search or "").strip()
    if search:
        where.append("(p.name LIKE %s OR IFNULL(p.sku, '') LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like])
    cur.execute(
        f"""
        SELECT p.id, p.name, p.sku, p.image, p.selling_price, p.stock_qty, p.tax_rate,
               p.unit, p.category, p.product_type
        FROM products p
        WHERE {" AND ".join(where)}
        ORDER BY p.name
        LIMIT 200
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    items = []
    for row in rows:
        items.append(
            {
                "id": row["id"],
                "name": row["name"],
                "sku": row["sku"] or "",
                "image": row["image"] or "",
                "price": _num(row["selling_price"]),
                "stock_qty": _num(row["stock_qty"]),
                "tax_rate": _num(row["tax_rate"]),
                "unit": row["unit"] or "pcs",
                "category": row.get("category") or "",
                "product_type": row.get("product_type") or "finished_goods",
            }
        )
    return items


def categories():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT category
        FROM products
        WHERE tenant_id=%s
          AND category IS NOT NULL AND TRIM(category) <> ''
          AND LOWER(IFNULL(status, 'active')) = 'active'
        ORDER BY category
        """,
        (tid(),),
    )
    rows = [r["category"] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def current_session(user_id):
    if not user_id:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, user_id, business_date, started_at, status
        FROM pos_sessions
        WHERE user_id=%s AND tenant_id=%s AND status='open'
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, tid()),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    biz = row["business_date"]
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "business_date": biz.isoformat() if hasattr(biz, "isoformat") else str(biz),
        "started_at": row["started_at"].isoformat(sep=" ") if row["started_at"] else None,
        "status": row["status"],
    }


def start_session(user_id):
    today = date.today()
    existing = current_session(user_id)
    if existing:
        return existing
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO pos_sessions (tenant_id, user_id, business_date, started_at, status)
            VALUES (%s, %s, %s, %s, 'open')
            """,
            (tid(), user_id, today, datetime.now()),
        )
        conn.commit()
        session_id = cur.lastrowid
    except Exception:
        conn.rollback()
        existing = current_session(user_id)
        if existing:
            return existing
        raise
    finally:
        cur.close()
        conn.close()
    return current_session(user_id) or {
        "id": session_id,
        "user_id": user_id,
        "business_date": today.isoformat(),
        "status": "open",
    }


def _next_bill_no(cur):
    year = datetime.now().strftime("%Y")
    lock_name = f"vera_pos_bill_{year}"
    cur.execute("SELECT GET_LOCK(%s, 10) AS locked", (lock_name,))
    lock = cur.fetchone()
    if not lock or not int(lock["locked"]):
        raise ValueError("Could not allocate POS bill number. Please retry.")
    cur.execute(
        """
        SELECT bill_no FROM pos_sales
        WHERE tenant_id=%s AND bill_no LIKE %s
        ORDER BY bill_no DESC
        LIMIT 1
        FOR UPDATE
        """,
        (tid(), "POS" + year + "%"),
    )
    row = cur.fetchone()
    if row and row["bill_no"]:
        last_seq = int(str(row["bill_no"])[-5:])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    return f"POS{year}{next_seq:05d}", lock_name


def complete_sale(user_id, customer_id, items, discount_amount, payment_mode, payments):
    session_row = current_session(user_id)
    if not session_row:
        raise ValueError("Start the business day first.")
    if not items:
        raise ValueError("Add at least one item to the cart.")

    prepared = []
    for raw in items:
        qty = _num(raw.get("qty"))
        price = _num(raw.get("price"))
        if qty <= 0 or price < 0:
            raise ValueError("Each cart line needs a quantity and price.")
        item_type = (raw.get("item_type") or "product").lower()
        if item_type not in ("product", "service", "quick"):
            item_type = "product"
        prepared.append(
            {
                "product_id": raw.get("product_id") or None,
                "item_type": item_type,
                "name": (raw.get("name") or "").strip() or "Item",
                "qty": qty,
                "price": price,
                "tax_rate": _num(raw.get("tax_rate")),
            }
        )

    subtotal = sum(i["qty"] * i["price"] for i in prepared)
    discount_amount = round(_num(discount_amount), 2)
    if discount_amount < 0:
        raise ValueError("Discount cannot be negative.")
    if discount_amount > subtotal:
        raise ValueError("Discount cannot exceed subtotal.")
    percent = (discount_amount / subtotal * 100.0) if subtotal else 0
    totals = calculate_document_totals(prepared, percent)
    grand = totals["grand_total"]

    payment_mode = (payment_mode or "cash").lower()
    if payment_mode not in ("cash", "upi", "split"):
        raise ValueError("Choose Cash, UPI, or split payment.")

    cleaned_payments = []
    for pay in payments or []:
        mode = (pay.get("mode") or pay.get("payment_mode") or "").lower()
        amount = round(_num(pay.get("amount")), 2)
        if amount <= 0:
            continue
        if mode not in ("cash", "upi"):
            raise ValueError("Split payments must be Cash or UPI.")
        cleaned_payments.append({"mode": mode, "amount": amount})
    if payment_mode != "split":
        cleaned_payments = [{"mode": payment_mode, "amount": grand}]
    paid = round(sum(p["amount"] for p in cleaned_payments), 2)
    if abs(paid - grand) > 0.05:
        raise ValueError("Payment total must match the grand total.")

    if customer_id:
        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError):
            customer_id = None
    else:
        customer_id = None

    conn = get_db_connection()
    cur = conn.cursor()
    lock_name = None
    try:
        for item in prepared:
            if item["item_type"] != "product" or not item["product_id"]:
                continue
            cur.execute(
                """
                SELECT name, stock_qty, tax_rate, selling_price
                FROM products WHERE id=%s AND tenant_id=%s FOR UPDATE
                """,
                (item["product_id"], tid()),
            )
            product = cur.fetchone()
            if not product:
                raise ValueError("A product in the cart is no longer available.")
            if _num(product["stock_qty"]) < item["qty"]:
                raise ValueError(f"Insufficient stock for {product['name']}.")
            item["tax_rate"] = _num(product["tax_rate"])
            item["name"] = product["name"]

        totals = calculate_document_totals(prepared, percent)
        grand = totals["grand_total"]
        paid = round(sum(p["amount"] for p in cleaned_payments), 2)
        if payment_mode != "split":
            cleaned_payments = [{"mode": payment_mode, "amount": grand}]
            paid = grand
        elif abs(paid - grand) > 0.05:
            raise ValueError("Payment total must match the grand total.")

        bill_no, lock_name = _next_bill_no(cur)
        cur.execute(
            """
            INSERT INTO pos_sales
            (tenant_id, bill_no, session_id, customer_id, sale_date, subtotal, discount_amount,
             gst_amount, total_amount, payment_mode, paid_amount, payment_status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Paid', %s)
            """,
            (
                tid(),
                bill_no,
                session_row["id"],
                customer_id,
                date.today(),
                totals["subtotal"],
                totals["discount_amount"],
                totals["gst_amount"],
                totals["grand_total"],
                payment_mode,
                paid,
                user_id,
            ),
        )
        sale_id = cur.lastrowid

        for item in prepared:
            cur.execute(
                """
                INSERT INTO pos_sale_items
                (tenant_id, pos_sale_id, product_id, item_type, name, qty, price, tax_rate, line_total, line_gst)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    tid(),
                    sale_id,
                    item["product_id"],
                    item["item_type"],
                    item["name"],
                    item["qty"],
                    item["price"],
                    item["tax_rate"],
                    item["line_total"],
                    item["line_gst"],
                ),
            )
            if item["item_type"] == "product" and item["product_id"]:
                cur.execute(
                    """
                    UPDATE products
                    SET stock_qty = stock_qty - %s
                    WHERE id = %s AND tenant_id = %s AND stock_qty >= %s
                    """,
                    (item["qty"], item["product_id"], tid(), item["qty"]),
                )
                if cur.rowcount == 0:
                    raise ValueError(f"Insufficient stock for {item['name']}.")
                cur.execute(
                    """
                    INSERT INTO stock_movements
                    (tenant_id, product_id, movement_type, quantity, reference_id, reference_type)
                    VALUES (%s, %s, 'sale', %s, %s, 'pos')
                    """,
                    (tid(), item["product_id"], -item["qty"], sale_id),
                )

        for pay in cleaned_payments:
            cur.execute(
                """
                INSERT INTO pos_payments (tenant_id, pos_sale_id, payment_mode, amount)
                VALUES (%s, %s, %s, %s)
                """,
                (tid(), sale_id, pay["mode"], pay["amount"]),
            )

        conn.commit()
        return {
            "id": sale_id,
            "bill_no": bill_no,
            "grand_total": totals["grand_total"],
            "gst_amount": totals["gst_amount"],
            "discount_amount": totals["discount_amount"],
            "subtotal": totals["subtotal"],
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        if lock_name:
            cur.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
        cur.close()
        conn.close()

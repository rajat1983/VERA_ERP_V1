from db import get_db_connection
from utils.tenant import tid


_TX_TABLES = (
    "purchase_items",
    "purchases",
    "sale_items",
    "sales_items",
    "sales",
    "payments",
    "vendor_payments",
    "pos_payments",
    "pos_sale_items",
    "pos_sales",
    "stock_movements",
)

_RESET_TABLES = _TX_TABLES + (
    "customers",
    "vendors",
    "products",
    "product_categories",
    "services",
    "service_categories",
)


def _has_table(cur, table):
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
        """,
        (table,),
    )
    return cur.fetchone()["c"] > 0


def _has_column(cur, table, column):
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cur.fetchone()["c"] > 0


def _delete_tenant_rows(cur, tables, tenant_id):
    for table in tables:
        if not _has_table(cur, table):
            continue
        if _has_column(cur, table, "tenant_id"):
            cur.execute(f"DELETE FROM `{table}` WHERE tenant_id=%s", (tenant_id,))
        elif table in ("purchase_items", "sale_items", "sales_items", "pos_sale_items", "pos_payments"):
            continue


def clear_transaction_data():
    tenant_id = tid()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        _delete_tenant_rows(cur, _TX_TABLES, tenant_id)
        if _has_table(cur, "products") and _has_column(cur, "products", "tenant_id"):
            cur.execute("UPDATE products SET stock_qty = 0 WHERE tenant_id=%s", (tenant_id,))
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def reset_database():
    tenant_id = tid()
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        _delete_tenant_rows(cur, _RESET_TABLES, tenant_id)
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

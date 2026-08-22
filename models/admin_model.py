from db import get_db_connection


def clear_transaction_data():

    conn = get_db_connection()
    cur = conn.cursor()

    try:

        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("TRUNCATE TABLE purchase_items")
        cur.execute("TRUNCATE TABLE purchases")
        try:
            cur.execute("TRUNCATE TABLE sale_items")
        except Exception:
            cur.execute("TRUNCATE TABLE sales_items")
        cur.execute("TRUNCATE TABLE sales")
        cur.execute("TRUNCATE TABLE stock_movements")
        try:
            cur.execute("TRUNCATE TABLE payments")
        except Exception:
            pass
        cur.execute("UPDATE products SET stock_qty = 0")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()


def reset_database():

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("TRUNCATE TABLE purchase_items")
        cur.execute("TRUNCATE TABLE purchases")
        try:
            cur.execute("TRUNCATE TABLE sale_items")
        except Exception:
            cur.execute("TRUNCATE TABLE sales_items")
        cur.execute("TRUNCATE TABLE sales")
        cur.execute("TRUNCATE TABLE stock_movements")
        try:
            cur.execute("TRUNCATE TABLE payments")
        except Exception:
            pass
        cur.execute("TRUNCATE TABLE customers")
        cur.execute("TRUNCATE TABLE vendors")
        cur.execute("TRUNCATE TABLE products")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()

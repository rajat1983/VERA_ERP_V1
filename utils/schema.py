from db import get_db_connection


def _has_column(cur, table, column):
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cur.fetchone()["c"] > 0


def _has_table(cur, table):
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        """,
        (table,),
    )
    return cur.fetchone()["c"] > 0


def _add_column(cur, table, column, ddl):
    if not _has_column(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def ensure_schema():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if _has_table(cur, "sales"):
            _add_column(cur, "sales", "gst_amount", "gst_amount DECIMAL(12,2) NOT NULL DEFAULT 0")
            _add_column(cur, "sales", "discount_amount", "discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0")
            _add_column(cur, "sales", "sale_status", "sale_status VARCHAR(20) NOT NULL DEFAULT 'Confirmed'")
            _add_column(cur, "sales", "payment_status", "payment_status VARCHAR(20) NOT NULL DEFAULT 'Pending'")
            _add_column(cur, "sales", "paid_amount", "paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0")

        if _has_table(cur, "purchases"):
            _add_column(cur, "purchases", "discount", "discount DECIMAL(10,2) NOT NULL DEFAULT 0")
            _add_column(cur, "purchases", "gst_amount", "gst_amount DECIMAL(12,2) NOT NULL DEFAULT 0")
            _add_column(cur, "purchases", "discount_amount", "discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0")
            _add_column(cur, "purchases", "status", "status VARCHAR(20) NOT NULL DEFAULT 'confirmed'")

        if _has_table(cur, "products"):
            _add_column(cur, "products", "tax_rate", "tax_rate DECIMAL(5,2) NOT NULL DEFAULT 0")
            _add_column(cur, "products", "hsn_code", "hsn_code VARCHAR(20) DEFAULT NULL")
            _add_column(cur, "products", "unit", "unit VARCHAR(20) DEFAULT 'pcs'")
            _add_column(cur, "products", "product_type", "product_type VARCHAR(40) DEFAULT 'finished_goods'")

        if _has_table(cur, "production_batches"):
            _add_column(cur, "production_batches", "status", "status VARCHAR(20) NOT NULL DEFAULT 'confirmed'")

        if not _has_table(cur, "payments"):
            cur.execute(
                """
                CREATE TABLE payments (
                    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    sale_id INT NOT NULL,
                    payment_date DATE NOT NULL,
                    amount DECIMAL(12,2) NOT NULL,
                    payment_mode VARCHAR(40) NOT NULL,
                    reference_no VARCHAR(80) DEFAULT NULL,
                    notes VARCHAR(255) DEFAULT NULL,
                    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        if not _has_table(cur, "users"):
            cur.execute(
                """
                CREATE TABLE users (
                    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(80) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

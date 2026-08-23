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


def _ensure_status_varchar(cur, table, column, default):
    """ENUM/short VARCHAR cannot store 'cancelled' (MySQL 1265)."""
    cur.execute(
        """
        SELECT DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    col = cur.fetchone()
    if not col:
        return
    data_type = (col["DATA_TYPE"] or "").lower()
    max_len = col["CHARACTER_MAXIMUM_LENGTH"]
    too_short = data_type == "enum" or (max_len is not None and int(max_len) < 20)
    if not too_short:
        return
    nullable = "NULL" if col["IS_NULLABLE"] == "YES" else "NOT NULL"
    if default not in ("confirmed", "Cancelled", "Pending"):
        default = "confirmed"
    cur.execute(
        f"ALTER TABLE `{table}` MODIFY COLUMN `{column}` VARCHAR(20) {nullable} DEFAULT '{default}'"
    )


def _ensure_roles_users(cur):
    if not _has_table(cur, "roles"):
        cur.execute(
            """
            CREATE TABLE roles (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(40) NOT NULL UNIQUE,
                description VARCHAR(255) DEFAULT NULL
            )
            """
        )
    for name, desc in (
        ("admin", "Full access including delete and administration"),
        ("manager", "Create and edit; no delete or cancel"),
        ("staff", "View all modules; add, edit, view and print sales"),
    ):
        cur.execute("SELECT id FROM roles WHERE name=%s", (name,))
        if not cur.fetchone():
            cur.execute("INSERT INTO roles (name, description) VALUES (%s, %s)", (name, desc))

    if not _has_table(cur, "users"):
        cur.execute(
            """
            CREATE TABLE users (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(120) DEFAULT NULL,
                email VARCHAR(120) DEFAULT NULL,
                mobile VARCHAR(20) DEFAULT NULL,
                photo VARCHAR(255) DEFAULT NULL,
                role_id INT NOT NULL,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                activation_token VARCHAR(64) DEFAULT NULL,
                activation_expires DATETIME DEFAULT NULL,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    else:
        _add_column(cur, "users", "is_active", "is_active TINYINT(1) NOT NULL DEFAULT 1")
        _add_column(cur, "users", "role_id", "role_id INT DEFAULT NULL")
        _add_column(cur, "users", "role", "role VARCHAR(20) DEFAULT NULL")
        _add_column(cur, "users", "full_name", "full_name VARCHAR(120) DEFAULT NULL")
        _add_column(cur, "users", "email", "email VARCHAR(120) DEFAULT NULL")
        _add_column(cur, "users", "mobile", "mobile VARCHAR(20) DEFAULT NULL")
        _add_column(cur, "users", "photo", "photo VARCHAR(255) DEFAULT NULL")
        cur.execute(
            """
            UPDATE users u
            JOIN roles r ON r.name = IFNULL(u.role, 'admin')
            SET u.role_id = r.id
            WHERE u.role_id IS NULL
            """
        )
        cur.execute("SELECT id FROM roles WHERE name='admin' LIMIT 1")
        admin_role = cur.fetchone()
        if admin_role:
            cur.execute("UPDATE users SET role_id=%s WHERE role_id IS NULL", (admin_role["id"],))

    _add_column(cur, "users", "full_name", "full_name VARCHAR(120) DEFAULT NULL")
    _add_column(cur, "users", "email", "email VARCHAR(120) DEFAULT NULL")
    _add_column(cur, "users", "mobile", "mobile VARCHAR(20) DEFAULT NULL")
    _add_column(cur, "users", "photo", "photo VARCHAR(255) DEFAULT NULL")
    _add_column(cur, "users", "status", "status VARCHAR(20) NOT NULL DEFAULT 'active'")
    _add_column(cur, "users", "activation_token", "activation_token VARCHAR(64) DEFAULT NULL")
    _add_column(cur, "users", "activation_expires", "activation_expires DATETIME DEFAULT NULL")
    cur.execute("UPDATE users SET status='active', is_active=1 WHERE status='approved'")
    cur.execute("UPDATE users SET status='active' WHERE status IS NULL OR status=''")


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
            _add_column(cur, "sales", "created_by", "created_by INT DEFAULT NULL")
            _ensure_status_varchar(cur, "sales", "sale_status", "Confirmed")
            _ensure_status_varchar(cur, "sales", "payment_status", "Pending")

        if _has_table(cur, "purchases"):
            _add_column(cur, "purchases", "discount", "discount DECIMAL(10,2) NOT NULL DEFAULT 0")
            _add_column(cur, "purchases", "gst_amount", "gst_amount DECIMAL(12,2) NOT NULL DEFAULT 0")
            _add_column(cur, "purchases", "discount_amount", "discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0")
            _add_column(cur, "purchases", "status", "status VARCHAR(20) NOT NULL DEFAULT 'confirmed'")
            _ensure_status_varchar(cur, "purchases", "status", "confirmed")

        if _has_table(cur, "products"):
            _add_column(cur, "products", "tax_rate", "tax_rate DECIMAL(5,2) NOT NULL DEFAULT 0")
            _add_column(cur, "products", "hsn_code", "hsn_code VARCHAR(20) DEFAULT NULL")
            _add_column(cur, "products", "unit", "unit VARCHAR(20) DEFAULT 'pcs'")
            _add_column(cur, "products", "product_type", "product_type VARCHAR(40) DEFAULT 'finished_goods'")

        if _has_table(cur, "production_batches"):
            _add_column(cur, "production_batches", "status", "status VARCHAR(20) NOT NULL DEFAULT 'confirmed'")
            _ensure_status_varchar(cur, "production_batches", "status", "confirmed")

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

        if not _has_table(cur, "audit_log"):
            cur.execute(
                """
                CREATE TABLE audit_log (
                    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    user_id INT DEFAULT NULL,
                    username VARCHAR(80) DEFAULT NULL,
                    action VARCHAR(40) NOT NULL,
                    module VARCHAR(40) NOT NULL,
                    entity VARCHAR(40) DEFAULT NULL,
                    entity_id INT DEFAULT NULL,
                    detail VARCHAR(500) DEFAULT NULL,
                    ip VARCHAR(45) DEFAULT NULL,
                    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        if _has_table(cur, "purchases"):
            _add_column(cur, "purchases", "paid_amount", "paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0")
            _add_column(cur, "purchases", "payment_status", "payment_status VARCHAR(20) NOT NULL DEFAULT 'Pending'")
            _ensure_status_varchar(cur, "purchases", "payment_status", "Pending")

        if _has_table(cur, "stock_movements"):
            _add_column(cur, "stock_movements", "remarks", "remarks VARCHAR(255) DEFAULT NULL")

        if not _has_table(cur, "vendor_payments"):
            cur.execute(
                """
                CREATE TABLE vendor_payments (
                    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    purchase_id INT NOT NULL,
                    payment_date DATE NOT NULL,
                    amount DECIMAL(12,2) NOT NULL,
                    payment_mode VARCHAR(40) NOT NULL,
                    reference_no VARCHAR(80) DEFAULT NULL,
                    notes VARCHAR(255) DEFAULT NULL,
                    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        _ensure_roles_users(cur)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def ensure_roles_users():
    """Always create login tables, even if other schema ALTERs fail."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        _ensure_roles_users(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

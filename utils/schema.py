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
            _add_column(cur, "products", "category", "category VARCHAR(80) DEFAULT NULL")
            _add_column(cur, "products", "short_name", "short_name VARCHAR(80) DEFAULT NULL")
            _add_column(cur, "products", "brand", "brand VARCHAR(80) DEFAULT NULL")
            _add_column(cur, "products", "barcode", "barcode VARCHAR(80) DEFAULT NULL")
            _add_column(cur, "products", "mrp", "mrp DECIMAL(12,2) DEFAULT NULL")
            _add_column(cur, "products", "low_stock_threshold", "low_stock_threshold INT NOT NULL DEFAULT 0")
            _add_column(cur, "products", "description", "description TEXT")
            _add_column(cur, "products", "notes", "notes TEXT")
            _ensure_product_categories(cur)

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
        _ensure_pos(cur)
        _ensure_services(cur)
        _ensure_tenants(cur)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def _ensure_product_categories(cur):
    if not _has_table(cur, "product_categories"):
        cur.execute(
            """
            CREATE TABLE product_categories (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(80) NOT NULL UNIQUE,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    if _has_table(cur, "products"):
        cur.execute(
            """
            INSERT IGNORE INTO product_categories (name)
            SELECT DISTINCT TRIM(category)
            FROM products
            WHERE category IS NOT NULL AND TRIM(category) <> ''
            """
        )


def _ensure_pos(cur):
    if not _has_table(cur, "pos_sessions"):
        cur.execute(
            """
            CREATE TABLE pos_sessions (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                business_date DATE NOT NULL,
                started_at DATETIME NOT NULL,
                ended_at DATETIME DEFAULT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'open',
                UNIQUE KEY uq_pos_session_user_day (user_id, business_date)
            )
            """
        )
    if not _has_table(cur, "pos_sales"):
        cur.execute(
            """
            CREATE TABLE pos_sales (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                bill_no VARCHAR(24) NOT NULL UNIQUE,
                session_id INT NOT NULL,
                customer_id INT DEFAULT NULL,
                sale_date DATE NOT NULL,
                subtotal DECIMAL(12,2) NOT NULL DEFAULT 0,
                discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                gst_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                payment_mode VARCHAR(40) NOT NULL,
                paid_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                payment_status VARCHAR(20) NOT NULL DEFAULT 'Paid',
                created_by INT DEFAULT NULL,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    if not _has_table(cur, "pos_sale_items"):
        cur.execute(
            """
            CREATE TABLE pos_sale_items (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                pos_sale_id INT NOT NULL,
                product_id INT DEFAULT NULL,
                item_type VARCHAR(20) NOT NULL DEFAULT 'product',
                name VARCHAR(200) NOT NULL,
                qty DECIMAL(12,3) NOT NULL,
                price DECIMAL(12,2) NOT NULL,
                tax_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
                line_total DECIMAL(12,2) NOT NULL,
                line_gst DECIMAL(12,2) NOT NULL DEFAULT 0
            )
            """
        )
    if not _has_table(cur, "pos_payments"):
        cur.execute(
            """
            CREATE TABLE pos_payments (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                pos_sale_id INT NOT NULL,
                payment_mode VARCHAR(40) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _ensure_services(cur):
    if not _has_table(cur, "services"):
        cur.execute(
            """
            CREATE TABLE services (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(160) NOT NULL,
                category VARCHAR(80) DEFAULT NULL,
                unit VARCHAR(40) NOT NULL DEFAULT 'page',
                price DECIMAL(12,2) NOT NULL DEFAULT 0,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
        )
    if not _has_table(cur, "service_categories"):
        cur.execute(
            """
            CREATE TABLE service_categories (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(80) NOT NULL UNIQUE,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    if _has_table(cur, "services"):
        cur.execute(
            """
            INSERT IGNORE INTO service_categories (name)
            SELECT DISTINCT TRIM(category)
            FROM services
            WHERE category IS NOT NULL AND TRIM(category) <> ''
            """
        )


_TENANT_TABLES = (
    "users",
    "company",
    "products",
    "product_categories",
    "customers",
    "vendors",
    "services",
    "service_categories",
    "employees",
    "sales",
    "sale_items",
    "purchases",
    "purchase_items",
    "payments",
    "vendor_payments",
    "stock_movements",
    "production_batches",
    "production_materials",
    "product_recipes",
    "pos_sessions",
    "pos_sales",
    "pos_sale_items",
    "pos_payments",
)


def _index_exists(cur, table, index_name):
    cur.execute(
        """
        SELECT COUNT(*) AS c
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    return cur.fetchone()["c"] > 0


def _drop_index(cur, table, index_name):
    if _index_exists(cur, table, index_name):
        cur.execute(f"ALTER TABLE `{table}` DROP INDEX `{index_name}`")


def _indexes_on_column(cur, table, column):
    cur.execute(
        """
        SELECT DISTINCT INDEX_NAME, NON_UNIQUE
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return cur.fetchall()


def _ensure_unique(cur, table, index_name, columns):
    if _index_exists(cur, table, index_name):
        return
    cols = ", ".join(f"`{c}`" for c in columns)
    cur.execute(f"ALTER TABLE `{table}` ADD UNIQUE KEY `{index_name}` ({cols})")


def _ensure_index(cur, table, index_name, columns):
    if _index_exists(cur, table, index_name):
        return
    cols = ", ".join(f"`{c}`" for c in columns)
    cur.execute(f"ALTER TABLE `{table}` ADD INDEX `{index_name}` ({cols})")


def _ensure_tenants(cur):
    if not _has_table(cur, "tenants"):
        cur.execute(
            """
            CREATE TABLE tenants (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                shop_code VARCHAR(16) NOT NULL,
                name VARCHAR(160) NOT NULL,
                slug VARCHAR(80) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_tenants_shop_code (shop_code),
                UNIQUE KEY uq_tenants_slug (slug)
            )
            """
        )
    if not _has_table(cur, "platform_users"):
        cur.execute(
            """
            CREATE TABLE platform_users (
                id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(120) NOT NULL,
                username VARCHAR(80) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(120) DEFAULT NULL,
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_platform_users_email (email),
                UNIQUE KEY uq_platform_users_username (username)
            )
            """
        )

    cur.execute("SELECT id FROM tenants WHERE shop_code=%s", ("SHOP0001",))
    default = cur.fetchone()
    if not default:
        name = "VERA Shop"
        if _has_table(cur, "company"):
            cur.execute("SELECT company_name FROM company LIMIT 1")
            row = cur.fetchone()
            if row and (row.get("company_name") or "").strip():
                name = row["company_name"].strip()
        cur.execute(
            """
            INSERT INTO tenants (shop_code, name, slug, status)
            VALUES ('SHOP0001', %s, 'shop0001', 'active')
            """,
            (name,),
        )
        default_id = cur.lastrowid
    else:
        default_id = default["id"]

    for table in _TENANT_TABLES:
        if not _has_table(cur, table):
            continue
        _add_column(cur, table, "tenant_id", "tenant_id INT NOT NULL DEFAULT 1")
        cur.execute(f"UPDATE `{table}` SET tenant_id=%s WHERE tenant_id IS NULL OR tenant_id=0", (default_id,))
        _ensure_index(cur, table, f"idx_{table}_tenant", ("tenant_id",))

    if _has_table(cur, "audit_log"):
        _add_column(cur, "audit_log", "tenant_id", "tenant_id INT DEFAULT NULL")
        cur.execute("UPDATE audit_log SET tenant_id=%s WHERE tenant_id IS NULL", (default_id,))
        _ensure_index(cur, "audit_log", "idx_audit_log_tenant", ("tenant_id",))

    if _has_table(cur, "users"):
        for idx in _indexes_on_column(cur, "users", "username"):
            if idx["NON_UNIQUE"] == 0 and idx["INDEX_NAME"] != "uq_users_tenant_username":
                cur.execute(
                    """
                    SELECT COUNT(*) AS c FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='users' AND INDEX_NAME=%s
                    """,
                    (idx["INDEX_NAME"],),
                )
                if cur.fetchone()["c"] == 1:
                    _drop_index(cur, "users", idx["INDEX_NAME"])
        for idx in _indexes_on_column(cur, "users", "email"):
            if idx["NON_UNIQUE"] == 0 and idx["INDEX_NAME"] not in (
                "uq_users_tenant_email",
                "PRIMARY",
            ):
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT COLUMN_NAME) AS c FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='users' AND INDEX_NAME=%s
                    """,
                    (idx["INDEX_NAME"],),
                )
                if cur.fetchone()["c"] == 1:
                    _drop_index(cur, "users", idx["INDEX_NAME"])
        _ensure_unique(cur, "users", "uq_users_tenant_username", ("tenant_id", "username"))

    if _has_table(cur, "product_categories"):
        for idx in _indexes_on_column(cur, "product_categories", "name"):
            if idx["NON_UNIQUE"] == 0 and idx["INDEX_NAME"] != "uq_product_categories_tenant_name":
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT COLUMN_NAME) AS c FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='product_categories' AND INDEX_NAME=%s
                    """,
                    (idx["INDEX_NAME"],),
                )
                if cur.fetchone()["c"] == 1:
                    _drop_index(cur, "product_categories", idx["INDEX_NAME"])
        _ensure_unique(
            cur, "product_categories", "uq_product_categories_tenant_name", ("tenant_id", "name")
        )

    if _has_table(cur, "products"):
        for idx in _indexes_on_column(cur, "products", "sku"):
            if idx["NON_UNIQUE"] == 0 and idx["INDEX_NAME"] != "uq_products_tenant_sku":
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT COLUMN_NAME) AS c FROM information_schema.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='products' AND INDEX_NAME=%s
                    """,
                    (idx["INDEX_NAME"],),
                )
                if cur.fetchone()["c"] == 1:
                    _drop_index(cur, "products", idx["INDEX_NAME"])
        _ensure_unique(cur, "products", "uq_products_tenant_sku", ("tenant_id", "sku"))


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

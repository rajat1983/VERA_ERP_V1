-- Optional rollback of unique keys added in Phase 1.
-- Do not drop tenant_id columns. Indexes can be re-added by ensure_schema().

ALTER TABLE sales DROP INDEX uq_sales_tenant_invoice;
ALTER TABLE purchases DROP INDEX uq_purchases_tenant_no;
ALTER TABLE pos_sales DROP INDEX uq_pos_sales_tenant_bill;
ALTER TABLE users DROP INDEX uq_users_tenant_email;
ALTER TABLE products DROP INDEX uq_products_tenant_barcode;
ALTER TABLE purchase_items DROP INDEX idx_purchase_items_parent;
ALTER TABLE sale_items DROP INDEX idx_sale_items_parent;
ALTER TABLE stock_movements DROP INDEX idx_stock_movements_ref;

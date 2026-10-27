-- Actual fixture DDL in Database.load.
CREATE TABLE orders(id VARCHAR PRIMARY KEY,tenant VARCHAR NOT NULL,created BIGINT NOT NULL);
CREATE TABLE messages(tenant VARCHAR NOT NULL,order_id VARCHAR NOT NULL,created BIGINT NOT NULL);
CREATE INDEX idx_orders_tenant_created ON orders(tenant,created DESC,id);
CREATE INDEX idx_messages_recent ON messages(tenant,order_id,created);

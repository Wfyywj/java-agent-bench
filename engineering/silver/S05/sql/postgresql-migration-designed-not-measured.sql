-- DESIGN ONLY: never executed in this benchmark. H2 does not validate PG behavior.
-- Concurrent index creation must be run outside a transaction block.
CREATE INDEX CONCURRENTLY idx_messages_recent ON messages(tenant,order_id,created);
CREATE INDEX CONCURRENTLY idx_orders_tenant_created ON orders(tenant,created DESC,id);
-- Inspect pg_index.indisvalid after completion; on interruption inspect invalid index before retry.
-- Rollback only these new indexes after verifying no dependent deployment requires them:
-- DROP INDEX CONCURRENTLY idx_messages_recent;
-- DROP INDEX CONCURRENTLY idx_orders_tenant_created;
-- Do not drop any preexisting index. CONCURRENTLY reduces write blocking but still takes
-- locks and uses CPU/IO; schedule with operational budgets and watch long transactions.

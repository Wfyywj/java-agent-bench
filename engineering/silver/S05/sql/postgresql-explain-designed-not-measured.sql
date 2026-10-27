-- DESIGN ONLY, NOT A CAPTURED QUERY PLAN. Run against fixed PG fixture before claiming PG readiness.
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT o.id,o.tenant,o.created FROM orders o
WHERE o.tenant='t1' AND EXISTS (
 SELECT 1 FROM messages m WHERE m.tenant=o.tenant AND m.order_id=o.id AND m.created>=1700
)
ORDER BY o.created DESC,o.id ASC LIMIT 100;
-- Check actual vs estimated rows and loops, qualifying tenant cardinality, spills/buffers,
-- index conditions, early LIMIT behavior and no application-side per-row query fan-out.
-- Exact plan node choice is data/engine dependent; do not assert a fixed optimizer shape.

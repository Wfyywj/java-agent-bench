# Frozen synthetic fixture decisions

Result requires a conversation at/after since and same tenant/order; EXISTS prevents duplicates with dense histories. Sort created DESC,id ASC, page limit 1..1000. Fixture includes empty conversations, tied creation timestamps and 80% dominant tenant.

Pending: H2 is not PostgreSQL; PostgreSQL EXPLAIN ANALYZE, production cardinality estimates, index lock duration, latency/SLO and connection pooling remain unmeasured. Counter covers search SQL, excludes fixture loading and EXPLAIN.

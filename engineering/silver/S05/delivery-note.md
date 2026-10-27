# Delivery and rollback

Actual H2 relational fixture, EXISTS semi-join, stable ordering, tenant predicate, counted SQL statements across page sizes, measured H2 EXPLAIN index evidence.

Use a fresh temporary data directory for each test. To restore a demo, stop the process and delete only its explicitly supplied test data directory, then rerun init/load. Do not replace production data or replay payment operations. Schema rollback proposals are design instructions, not executed migrations.

Residual limits: H2 is not PostgreSQL; PostgreSQL EXPLAIN ANALYZE, production cardinality estimates, index lock duration, latency/SLO and connection pooling remain unmeasured. Counter covers search SQL, excludes fixture loading and EXPLAIN.

Do not infer catalog readiness, model capability, hidden evaluation quality or production safety from these public development checks.

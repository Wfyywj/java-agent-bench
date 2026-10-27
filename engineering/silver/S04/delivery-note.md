# Delivery and rollback

Actual H2 JDBC transaction and JDK dynamic proxy entry; batch-row locking, stock/orders atomic rollback, checked/runtime injection, independent concurrent connections for cancellation versus shipping.

Use a fresh temporary data directory for each test. To restore a demo, stop the process and delete only its explicitly supplied test data directory, then rerun init/load. Do not replace production data or replay payment operations. Schema rollback proposals are design instructions, not executed migrations.

Residual limits: H2 is not PostgreSQL. JDK Proxy is not Spring AOP: Spring self-invocation, propagation configuration and connection-pool exhaustion remain unmeasured. One fixture batch; no production lock/load calibration.

Do not infer catalog readiness, model capability, hidden evaluation quality or production safety from these public development checks.

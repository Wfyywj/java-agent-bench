# Repair S04's Spring transaction boundary

In this synthetic batch-delivery service, cancellation sometimes releases inventory while leaving an incompletely cancelled batch. Diagnose the real proxy boundary and failure behavior, then repair only the listed Java sources. Preserve public signatures and the injected OperationProbe seam.

Required: cancellation is atomic, including checked BusinessFailure and runtime exceptions after partial work; repeated cancellation releases stock once; any delivered order rejects the entire cancellation. Delivery and cancellation serialize per batch, permitting exactly one terminal winner. Unrelated batches must remain usable, and shared-SKU inventory increments must not lose updates. Use actual Spring annotation-driven transactions, per-batch SQL row locking, and JDBC, not mocked transaction flags or in-memory state.

Deliver source package `src/bench/*.java` using agent-files.json targets plus requirement-decisions.md, evidence-map.md, regression-tests/ and delivery-note.md. Evaluator-owned tests cannot be replaced. H2 is the executable narrowed target; PostgreSQL and bounded pool coverage remain explicitly outstanding. No production data, external communication, system configuration changes or model calls.

# Evidence map

Main -> TransactionEntry JDK Proxy -> BatchService.execute -> H2 batch/orders/inventory. Proxy rolls back InvocationTargetException including checked/runtime causes.

The baseline explicitly commits the first order/stock writes before throwing: rollback cannot undo already committed data. This reproduces partial commit, not a claim to reproduce Spring self-invocation. Retain batch-level lock, not table-wide lock.

`fixtures/cases.json` maps each scenario to original acceptance IDs, but passing mapped assertions only covers the narrowed executable slice, not the entire criterion. Actual outcomes: `evidence/selfcheck.json`. All source variants are compiled independently. Three reference runs repeat acceptance outcomes; S04 intentionally allows either legal concurrent winner.

Unmeasured: H2 is not PostgreSQL. JDK Proxy is not Spring AOP: Spring self-invocation, propagation configuration and connection-pool exhaustion remain unmeasured. One fixture batch; no production lock/load calibration.

# S05 engineering slice

Actual H2 relational fixture, EXISTS semi-join, stable ordering, tenant predicate, counted SQL statements across page sizes, measured H2 EXPLAIN index evidence.

**Not full-catalog ready.** H2 is not PostgreSQL; PostgreSQL EXPLAIN ANALYZE, production cardinality estimates, index lock duration, latency/SLO and connection pooling remain unmeasured. Counter covers search SQL, excludes fixture loading and EXPLAIN.

- Selfcheck: `python3 run_selfcheck.py` (baseline must fail; reference must pass 3 runs; all compiling mutants must be killed).
- Candidate: `python3 run_selfcheck.py --candidate ABS_PACKAGE` (JSON, exit 0 only on all behavioral checks).
- 9 public black-box scenarios. Oracle owns fixed expected outputs / independently computed relational sets, not reference-generated answers.
- Source snapshots: `baseline/src`, `reference/src`, `mutants/*/src`.
- Exact original contract: `original-task.json`; explicit narrowed scope: `task.json`.
- Evidence: `evidence/selfcheck.json`, including actual command traces, per-variant source digest, compile errors if any and residual limits.

The CLI uses status-like strings but is not HTTP. Clean temporary data directories are recreated for every scenario and run; Candidate runtime heaps are 128 MiB (compiler uses the host JVM default), per-command timeout 15 s, compiler timeout 45 s, combined output limit 128 KiB. JDK 21 target/source are explicit because this runtime lacks release-symbol metadata. No wall-clock speed claims or benchmarked model rankings.

## Independent audit hardening
Query-budget acceptance uses `evaluator/TrustedSearchProbe.java`, not the candidate-maintained `queries` field. A separately compiled evaluator-owned wrapper counts actual JDBC statement execute calls on the provided connection and checks the returned IDs against the independent oracle. CLI behavior remains separately checked. Additional compiling mutants cover uncounted N+1 execution and exclusive `>` instead of inclusive `>=` at timestamp 1800. The probe is evaluator-owned and excluded from `agent-files.json`. This is trusted-code semantic instrumentation, not a malicious-code security boundary (e.g. deliberate connection unwrapping is not sandboxed).

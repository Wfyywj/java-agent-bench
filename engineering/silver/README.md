# Silver engineering development pack

Five original Java 21 engineering slices, explicitly narrower than catalog contracts. These are public development fixtures, not hidden tests, model results, or production-readiness certification.

| Task | Actual executable substrate | Main unmeasured boundary |
|---|---|---|
| S01 | HMAC callback CLI + persistent atomic snapshot | Real DB/payment/HTTP delivery |
| S02 | Independently compiled SDK/gateway/service directories | Real repositories/deployment telemetry |
| S03 | File-backed authorization and export worker | HTTP authentication/object storage |
| S04 | H2 JDBC, JDK transaction proxy, independent concurrent connections | Spring AOP and PostgreSQL |
| S05 | H2 SQL, counted queries, actual EXPLAIN | PostgreSQL plans, production latency |

```sh
python3 engineering/silver/setup_h2.py  # explicit opt-in pinned Maven dependency; no system install
python3 engineering/silver/run_all.py
python3 engineering/silver/S04/run_selfcheck.py --candidate /absolute/submission
```

H2 jar location defaults to `/tmp/java-agent-bench-h2-2.3.232.jar` and can be set with `BENCH_H2_JAR`. Exact SHA256 is pinned in setup_h2.py and verifier.py. Evaluation itself is offline and never downloads dependencies. Jar excluded from repository.

Each package preserves the original catalog task and states implemented scope separately. Source mutations are independent compiling business faults. Each reference is rerun three times from clean data directories. S04 race may pick either legal winner; deterministic means invariant/acceptance outcomes, not scheduling identity.

Candidates are **trusted local code only**. Timeouts, heap/output limits and clean directories are not a security sandbox, and a malicious candidate can inspect the public evaluator. No isolation or contamination-resistance claim. `agent-files.json` documents safe model workspace preparation and excludes reference, mutation, evidence and full expected-output oracle files. Baseline and reference can both be evaluated through the same arbitrary-candidate interface.

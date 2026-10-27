# Gold engineering fixture pack (public development slices)

These are original, dependency-free Java 21 service-module fixtures, not claims of full catalog readiness or measured model difficulty. Every task retains original context and acceptance criteria in `task.json` alongside narrower implemented scope. The executable adapters are deliberately local; they are not MySQL, Kafka, Redis or production object storage.

## Run

From a task directory:

```
python3 selfcheck.py                    # G01–G04 reference/base/mutants, three clean repeats
python3 run_selfcheck.py --candidate /absolute/trusted/candidate
```

G05 additionally documents its own calibration command in `task.json` / README. `agent-files.json` is an explicit source → target allowlist for preparing a candidate. Do not copy reference, verifier, mutations or expected-output evidence into agent inputs. Parent harness may invoke the evaluator-side candidate command. Candidate sources can be reorganized but must preserve public APIs.

Each evaluation compiles freshly through `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21`, then executes in a clean temporary working directory. No Maven downloads, installs or external services. Process time, heap and captured output budgets are enforced; G01–G04 kill process groups on timeout/output overflow. This is **not a hostile-code sandbox**. Use externally isolated disposable containers with network disabled and no credentials for untrusted submissions. A Java program runs with the evaluator's OS permissions.

## Evidence and limits

`verification-results.json` contains actual per-repeat outputs and failures. Reference values are asserted directly from frozen business rules, not captured as golden output from the reference. Deliberate semantic mutants calibrate specific sensitivity; they do not establish completeness. The baseline shares a documented deliberate defect with one mutant. Reference, baseline and tests were authored in this task; no separate human-author independence is claimed.

All verification is **public development**. There are no hidden cases in this repository. Agent packaging hides evaluator files from a prepared workspace, but this alone does not convert a public suite into an independent holdout. Full unseen-case evaluation, real dependency integrations, independent review, operational performance calibration and model pilots remain future work.

| Task | Real mechanisms executed | Important original-scope gaps |
|---|---|---|
| G01 | Independently persisted order/inventory append logs; replay; unknown reply query; lease-capacity locking; recovery authorization | crash before compensation intent; multi-process storage; event-version/poison partitions; full manual reconciliation |
| G02 | Three-module exact-arithmetic billing; calendar/DST segmentation; version/input snapshots; audited no-payment rebuild diffs | durable history database; actual approval/authentication; real payments |
| G03 | HMAC protocol versions; on-disk chunks/objects; out-of-order assembly; independent stored/full hash checks; attachment gating; cleanup pause | durable session metadata/restart resume; object-store transactions; rolling deployment matrix |
| G04 | SDK cache and two callers; ordinary-account isolation exploit; lost invalidation TTL; outage/version regressions; structured PR review | unresolved production SLA; real identity/Redis; bounded cache-size/load validation |
| G05 | Real bounded ThreadPoolExecutors, deterministic latch wait graph, bulkhead isolation, cancellation and shutdown | see G05 manifest: synthetic connection resource and explicit deadline cancellation |

# G05 public development verification

Environment: OpenJDK 21.0.12.1; standard library only. Compiler launched through `java -m jdk.compiler/com.sun.tools.javac.Main`, `-source 21 -target 21`. No dependency installs or network calls.

| Variant | Repeat 1 | Repeat 2 | Repeat 3 |
|---|---|---|---|
| reference | PASS 16/16 | PASS 16/16 | PASS 16/16 |
| baseline | REJECTED | REJECTED | REJECTED |
| mutants/cancelled_queue_leak | REJECTED | REJECTED | REJECTED |
| mutants/lost_shutdown_futures | REJECTED | REJECTED | REJECTED |
| mutants/result_defaulting | REJECTED | REJECTED | REJECTED |
| mutants/shared_bulkhead | REJECTED | REJECTED | REJECTED |
| mutants/unbounded_queue | REJECTED | REJECTED | REJECTED |

All seven variants compile. Every incident subprocess succeeds. The reference passes all 16 invariant groups in three independent temporary compile/run workspaces. Baseline and all five mutants are rejected each time. No watchdog timeout or output-limit termination occurred at runner-process level. Test-level 2-second watchdog failures are retained in baseline/shared-bulkhead diagnostics.

Mutation evidence: cancelled queue leak -> I10; lost shutdown futures -> I13; shared bulkhead -> I06; unbounded queue -> I02 and I07; result defaulting -> I03, I04, I06, I09, I15 and I16. Baseline has the original parent-waits-for-same-pool-child structure. Exact baseline failure count is not a performance metric; see individual outputs.

These are disclosed development tests, not hidden acceptance. No model rollout, production load, real network/connection-pool cancellation, database, deployment or rollback was performed. The original G05 catalog remains broader than this runnable slice. Raw outputs are in `verification-results.json`. JVM object addresses in exception messages vary between repeats; pass/reject outcomes are stable.

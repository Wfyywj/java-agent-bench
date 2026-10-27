# K04: Peak booking recovery and coordinated admission

Repair the multi-file Java 21 service in `src/`. Preserve the public CLI and frozen policy. Do not edit the verifier. Deliver a diagnosis, bounded patch, regression evidence, rollout/rollback note, and explicitly unverified risks.

## Candidate entrypoint
Compile all `src/*.java` with `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21 -d classes ...`. Invoke `java -cp classes Main JOURNAL_PATH "COMMAND" [before|after]`. Each invocation is a fresh process. Success writes one durable command before returning; rejected commands do not enter the journal. `before` simulates interruption before commit, `after` response loss after commit; both return UNKNOWN. Query commands are replay-safe and currently logged too.

Commands: `database true|false; failover; book TOKEN TENANT TERM RETRY_BUDGET; deliver TOKEN; query TOKEN; repair EXPECTED_TERM [apply]; status`. Tokens are space-delimited ASCII, no real customer data. Errors use `REJECT reason`.

## Frozen contract
Capacity is three. Only tenant member is authorized. Retry budget 1..2 is an end-to-end envelope, never multiplied by layers. Database fault refuses writes. Failover increments connection term; stale clients must refresh. Retrying an acknowledged token does not consume capacity. Delivery deduplicates side effects. Unknown post-commit results are discoverable by query. Repair defaults to dry-run and requires current term; repeated apply fills missing delivery projections once.

## Delivery phases
1. Diagnose the starter defect and identify business invariants; record unresolved policy instead of inventing it.
2. Implement with file-lock serialization, checksummed journal records, forced writes, and restart reconstruction. Do not silently truncate corrupt/torn records; block and request recovery.
3. Rehearse the fault boundary before/after append, retries, stale inputs, replay and domain-specific cutover.
4. Perform rollback/recovery only within the frozen contract and reconcile final state.
5. Produce evidence-map.md and delivery-note.md, separating executed assertions from untested infrastructure.

## Scope boundary
No actual DB connection pool, load generator, latency SLO, real notifications, or reversible external effects. Repair can restore missing in-log delivery projections only; it cannot repair arbitrary production data or undo already delivered external messages.

This is a runnable engineering slice, not a full king-tier task or calibrated difficulty. Public development tests only. Candidate execution is trusted-local-code only, not a secure sandbox.

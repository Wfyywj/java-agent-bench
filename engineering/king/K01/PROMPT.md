# K01: Entitlement ledger fenced failover

Repair the multi-file Java 21 service in `src/`. Preserve the public CLI and frozen policy. Do not edit the verifier. Deliver a diagnosis, bounded patch, regression evidence, rollout/rollback note, and explicitly unverified risks.

## Candidate entrypoint
Compile all `src/*.java` with `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21 -d classes ...`. Invoke `java -cp classes Main JOURNAL_PATH "COMMAND" [before|after]`. Each invocation is a fresh process. Success writes one durable command before returning; rejected commands do not enter the journal. `before` simulates interruption before commit, `after` response loss after commit; both return UNKNOWN. Query commands are replay-safe and currently logged too.

Commands: `promote REGION TERM; grant REGION TERM TOKEN POSITIVE_AMOUNT; network true|false; control true|false; rollback REGION; status`. Tokens are space-delimited ASCII, no real customer data. Errors use `REJECT reason`.

## Frozen contract
Freeze availability policy: grants require reachable modeled control and replication paths. Bootstrap A at term 1. Partition denies confirmation, then restore links, promote B at a greater term, reject old A, and roll back by a new term. Successful grants synchronously advance both modeled replicas. Token reuse with different amount conflicts. Balance additions use checked arithmetic.

## Delivery phases
1. Diagnose the starter defect and identify business invariants; record unresolved policy instead of inventing it.
2. Implement with file-lock serialization, checksummed journal records, forced writes, and restart reconstruction. Do not silently truncate corrupt/torn records; block and request recovery.
3. Rehearse the fault boundary before/after append, retries, stale inputs, replay and domain-specific cutover.
4. Perform rollback/recovery only within the frozen contract and reconcile final state.
5. Produce evidence-map.md and delivery-note.md, separating executed assertions from untested infrastructure.

## Scope boundary
A single OS-locked journal stands in for the linearization authority. Replica balances are modeled in the same log: no consensus implementation, asynchronous replication lag, one-way transport partition, separate disks, or real cloud RPO/RTO. No RPO/RTO number is a measured claim.

This is a runnable engineering slice, not a full king-tier task or calibrated difficulty. Public development tests only. Candidate execution is trusted-local-code only, not a secure sandbox.

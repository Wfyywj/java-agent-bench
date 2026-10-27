# K05: Settlement phased compatibility and reconciliation

Repair the multi-file Java 21 service in `src/`. Preserve the public CLI and frozen policy. Do not edit the verifier. Deliver a diagnosis, bounded patch, regression evidence, rollout/rollback note, and explicitly unverified risks.

## Candidate entrypoint
Compile all `src/*.java` with `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21 -d classes ...`. Invoke `java -cp classes Main JOURNAL_PATH "COMMAND" [before|after]`. Each invocation is a fresh process. Success writes one durable command before returning; rejected commands do not enter the journal. `before` simulates interruption before commit, `after` response loss after commit; both return UNKNOWN. Query commands are replay-safe and currently logged too.

Commands: `policy fee-merchant; consumer VERSION; producer VERSION; order ITEM GROSS; refund TOKEN ITEM AMOUNT; settle ITEM TIME; reconcile ITEM; status`. Tokens are space-delimited ASCII, no real customer data. Errors use `REJECT reason`.

## Frozen contract
Freeze synthetic fee-owner policy before financial writes. Refund per item with a globally unique token; conflicting token payload rejects. Refund sum cannot exceed gross. Settlement is allowed at time >=100, locks refunds, and leaves a durable PENDING obligation. Repeat settle does not dispatch a new payment. Reconcile transitions pending to paid exactly once. Upgrade consumer before producer and roll producer back before consumer. Conservation: gross=refunded+paid+remaining.

## Delivery phases
1. Diagnose the starter defect and identify business invariants; record unresolved policy instead of inventing it.
2. Implement with file-lock serialization, checksummed journal records, forced writes, and restart reconstruction. Do not silently truncate corrupt/torn records; block and request recovery.
3. Rehearse the fault boundary before/after append, retries, stale inputs, replay and domain-specific cutover.
4. Perform rollback/recovery only within the frozen contract and reconcile final state.
5. Produce evidence-map.md and delivery-note.md, separating executed assertions from untested infrastructure.

## Scope boundary
Local payment obligation, not real external payment idempotency. Five teams are represented by domain boundaries, not five independent repos/databases. No fee amount calculation, heterogeneous serializers, distributed transaction, real customer funds, or simultaneous provider callback implementation.

This is a runnable engineering slice, not a full king-tier task or calibrated difficulty. Public development tests only. Candidate execution is trusted-local-code only, not a secure sandbox.

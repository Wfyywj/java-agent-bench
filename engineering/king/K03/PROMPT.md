# K03: Billing engine differential replay and rollback

Repair the multi-file Java 21 service in `src/`. Preserve the public CLI and frozen policy. Do not edit the verifier. Deliver a diagnosis, bounded patch, regression evidence, rollout/rollback note, and explicitly unverified risks.

## Candidate entrypoint
Compile all `src/*.java` with `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21 -d classes ...`. Invoke `java -cp classes Main JOURNAL_PATH "COMMAND" [before|after]`. Each invocation is a fresh process. Success writes one durable command before returning; rejected commands do not enter the journal. `before` simulates interruption before commit, `after` response loss after commit; both return UNKNOWN. Query commands are replay-safe and currently logged too.

Commands: `approve peak-correction; shadow PEAK OFFPEAK; cutover TENANT PERIOD; rollback TENANT PERIOD; bill TENANT PERIOD PEAK OFFPEAK; status`. Tokens are space-delimited ASCII, no real customer data. Errors use `REJECT reason`.

## Frozen contract
Frozen synthetic tariff: v1 uses 2 units for all consumption; approved v2 uses peak=3/offpeak=2. Negative readings are missing and must reject. Shadow computes both without issuing bills. Unapproved differences block traffic expansion. Cutover is tenant+period scoped. Confirmed bills pin snapshot, amount, and rule forever, including after rollback. Changed readings require a separate adjustment flow (not implemented), never reinterpretation.

## Delivery phases
1. Diagnose the starter defect and identify business invariants; record unresolved policy instead of inventing it.
2. Implement with file-lock serialization, checksummed journal records, forced writes, and restart reconstruction. Do not silently truncate corrupt/torn records; block and request recovery.
3. Rehearse the fault boundary before/after append, retries, stale inputs, replay and domain-specific cutover.
4. Perform rollback/recovery only within the frozen contract and reconcile final state.
5. Produce evidence-map.md and delivery-note.md, separating executed assertions from untested infrastructure.

## Scope boundary
No real historical scripts, taxes, time-zone bucketing, rule-effective timestamp import, customer communication, or production performance budget. Integer aggregate readings and one approved policy correction are the executable slice.

This is a runnable engineering slice, not a full king-tier task or calibrated difficulty. Public development tests only. Candidate execution is trusted-local-code only, not a secure sandbox.

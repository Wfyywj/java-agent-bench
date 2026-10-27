# K02: Privacy deletion saga with retained audit

Repair the multi-file Java 21 service in `src/`. Preserve the public CLI and frozen policy. Do not edit the verifier. Deliver a diagnosis, bounded patch, regression evidence, rollout/rollback note, and explicitly unverified risks.

## Candidate entrypoint
Compile all `src/*.java` with `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21 -d classes ...`. Invoke `java -cp classes Main JOURNAL_PATH "COMMAND" [before|after]`. Each invocation is a fresh process. Success writes one durable command before returning; rejected commands do not enter the journal. `before` simulates interruption before commit, `after` response loss after commit; both return UNKNOWN. Query commands are replay-safe and currently logged too.

Commands: `write SUBJECT VERSION PAYLOAD; delete SUBJECT VERSION; step SUBJECT users|search|objects|analytics; proof SUBJECT; restore SUBJECT STORE PAYLOAD; view SUBJECT`. Tokens are space-delimited ASCII, no real customer data. Errors use `REJECT reason`.

## Frozen contract
Subject tombstone must precede all deletion work. Four independently completed projections are required before COMPLETE. Retries and lower-version manifests cannot reduce the deletion watermark. Tombstones block all later writes including newer versions; synthetic policy requires a separately authorized new identity for re-enrollment. Backup restore must filter using the durable manifest. Retain receipt version only, not supplied payload, in the audit projection.

## Delivery phases
1. Diagnose the starter defect and identify business invariants; record unresolved policy instead of inventing it.
2. Implement with file-lock serialization, checksummed journal records, forced writes, and restart reconstruction. Do not silently truncate corrupt/torn records; block and request recovery.
3. Rehearse the fault boundary before/after append, retries, stale inputs, replay and domain-specific cutover.
4. Perform rollback/recovery only within the frozen contract and reconcile final state.
5. Produce evidence-map.md and delivery-note.md, separating executed assertions from untested infrastructure.

## Scope boundary
Synthetic policy, not legal guidance. Logical projections share one journal; this does not certify deletion of raw journal or backups, actual blob erasure, cryptographic deletion, retention expiration, or independent services. Payloads are synthetic fixture values only; production PII is forbidden.

This is a runnable engineering slice, not a full king-tier task or calibrated difficulty. Public development tests only. Candidate execution is trusted-local-code only, not a secure sandbox.

# Phase contract and risk ledger

Freeze synthetic fee-owner policy before financial writes. Refund per item with a globally unique token; conflicting token payload rejects. Refund sum cannot exceed gross. Settlement is allowed at time >=100, locks refunds, and leaves a durable PENDING obligation. Repeat settle does not dispatch a new payment. Reconcile transitions pending to paid exactly once. Upgrade consumer before producer and roll producer back before consumer. Conservation: gross=refunded+paid+remaining.

## Crash contract
The filesystem must preserve successfully forced file writes and cooperative OS file locking. `before` leaves no new record; `after` may commit but loses its response. Restart is mandatory between requests. Complete checksummed records replay in order. A torn/corrupt tail blocks service rather than pretending the write was absent. Operator journal recovery is deliberately not automatic. Parent-directory fsync and sudden disk/power loss are not promised.

## Original versus realized
See task.json for the verbatim original catalog scope. Local payment obligation, not real external payment idempotency. Five teams are represented by domain boundaries, not five independent repos/databases. No fee amount calculation, heterogeneous serializers, distributed transaction, real customer funds, or simultaneous provider callback implementation.

## Check evidence
The independent Python verifier drives the process and compares exact output and resulting state across restart boundaries. Reference, starter and four targeted semantic mutants run three times in fresh temporary directories. selfcheck-evidence.json contains commands, expectations, actual output and source digests; a killed mutant does not calibrate model difficulty.

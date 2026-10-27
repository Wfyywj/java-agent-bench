# Phase contract and risk ledger

Capacity is three. Only tenant member is authorized. Retry budget 1..2 is an end-to-end envelope, never multiplied by layers. Database fault refuses writes. Failover increments connection term; stale clients must refresh. Retrying an acknowledged token does not consume capacity. Delivery deduplicates side effects. Unknown post-commit results are discoverable by query. Repair defaults to dry-run and requires current term; repeated apply fills missing delivery projections once.

## Crash contract
The filesystem must preserve successfully forced file writes and cooperative OS file locking. `before` leaves no new record; `after` may commit but loses its response. Restart is mandatory between requests. Complete checksummed records replay in order. A torn/corrupt tail blocks service rather than pretending the write was absent. Operator journal recovery is deliberately not automatic. Parent-directory fsync and sudden disk/power loss are not promised.

## Original versus realized
See task.json for the verbatim original catalog scope. No actual DB connection pool, load generator, latency SLO, real notifications, or reversible external effects. Repair can restore missing in-log delivery projections only; it cannot repair arbitrary production data or undo already delivered external messages.

## Check evidence
The independent Python verifier drives the process and compares exact output and resulting state across restart boundaries. Reference, starter and three targeted semantic mutants run three times in fresh temporary directories. selfcheck-evidence.json contains commands, expectations, actual output and source digests; a killed mutant does not calibrate model difficulty.

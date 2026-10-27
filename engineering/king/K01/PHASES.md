# Phase contract and risk ledger

Freeze availability policy: grants require reachable modeled control and replication paths. Bootstrap A at term 1. Partition denies confirmation, then restore links, promote B at a greater term, reject old A, and roll back by a new term. Successful grants synchronously advance both modeled replicas. Token reuse with different amount conflicts. Balance additions use checked arithmetic.

## Crash contract
The filesystem must preserve successfully forced file writes and cooperative OS file locking. `before` leaves no new record; `after` may commit but loses its response. Restart is mandatory between requests. Complete checksummed records replay in order. A torn/corrupt tail blocks service rather than pretending the write was absent. Operator journal recovery is deliberately not automatic. Parent-directory fsync and sudden disk/power loss are not promised.

## Original versus realized
See task.json for the verbatim original catalog scope. A single OS-locked journal stands in for the linearization authority. Replica balances are modeled in the same log: no consensus implementation, asynchronous replication lag, one-way transport partition, separate disks, or real cloud RPO/RTO. No RPO/RTO number is a measured claim.

## Check evidence
The independent Python verifier drives the process and compares exact output and resulting state across restart boundaries. Reference, starter and three targeted semantic mutants run three times in fresh temporary directories. selfcheck-evidence.json contains commands, expectations, actual output and source digests; a killed mutant does not calibrate model difficulty.

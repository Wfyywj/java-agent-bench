# Phase contract and risk ledger

Subject tombstone must precede all deletion work. Four independently completed projections are required before COMPLETE. Retries and lower-version manifests cannot reduce the deletion watermark. Tombstones block all later writes including newer versions; synthetic policy requires a separately authorized new identity for re-enrollment. Backup restore must filter using the durable manifest. Retain receipt version only, not supplied payload, in the audit projection.

## Crash contract
The filesystem must preserve successfully forced file writes and cooperative OS file locking. `before` leaves no new record; `after` may commit but loses its response. Restart is mandatory between requests. Complete checksummed records replay in order. A torn/corrupt tail blocks service rather than pretending the write was absent. Operator journal recovery is deliberately not automatic. Parent-directory fsync and sudden disk/power loss are not promised.

## Original versus realized
See task.json for the verbatim original catalog scope. Synthetic policy, not legal guidance. Logical projections share one journal; this does not certify deletion of raw journal or backups, actual blob erasure, cryptographic deletion, retention expiration, or independent services. Payloads are synthetic fixture values only; production PII is forbidden.

## Check evidence
The independent Python verifier drives the process and compares exact output and resulting state across restart boundaries. Reference, starter and three targeted semantic mutants run three times in fresh temporary directories. selfcheck-evidence.json contains commands, expectations, actual output and source digests; a killed mutant does not calibrate model difficulty.

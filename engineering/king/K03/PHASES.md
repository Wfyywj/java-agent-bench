# Phase contract and risk ledger

Frozen synthetic tariff: v1 uses 2 units for all consumption; approved v2 uses peak=3/offpeak=2. Negative readings are missing and must reject. Shadow computes both without issuing bills. Unapproved differences block traffic expansion. Cutover is tenant+period scoped. Confirmed bills pin snapshot, amount, and rule forever, including after rollback. Changed readings require a separate adjustment flow (not implemented), never reinterpretation.

## Crash contract
The filesystem must preserve successfully forced file writes and cooperative OS file locking. `before` leaves no new record; `after` may commit but loses its response. Restart is mandatory between requests. Complete checksummed records replay in order. A torn/corrupt tail blocks service rather than pretending the write was absent. Operator journal recovery is deliberately not automatic. Parent-directory fsync and sudden disk/power loss are not promised.

## Original versus realized
See task.json for the verbatim original catalog scope. No real historical scripts, taxes, time-zone bucketing, rule-effective timestamp import, customer communication, or production performance budget. Integer aggregate readings and one approved policy correction are the executable slice.

## Check evidence
The independent Python verifier drives the process and compares exact output and resulting state across restart boundaries. Reference, starter and four targeted semantic mutants run three times in fresh temporary directories. selfcheck-evidence.json contains commands, expectations, actual output and source digests; a killed mutant does not calibrate model difficulty.

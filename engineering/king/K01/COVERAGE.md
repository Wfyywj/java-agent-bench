# Original acceptance coverage (partial, not full acceptance)

- K01-A01: documentation only: no measured RPO/RTO.
- K01-A02: grant guards, stale-writer mutant, restart and concurrent token race.
- K01-A03: before/after durable append and retry assertions; file force fault model only.
- K01-A04: logged promotion/rollback/term replay; no asynchronous catch-up.
- K01-A05: modeled disconnected link and control unavailability; no asymmetric transport or real lag.
- K01-A06: exact balances and torn-tail block; no real cloud exercise.

Evidence lives in selfcheck-evidence.json. Public checks validate the declared slice, not every original acceptance criterion.

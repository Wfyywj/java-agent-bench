# Original acceptance coverage (partial, not full acceptance)

- K04-A01: separate database, connection-term, delivery and retry histories.
- K04-A02: authorization, capacity and overload budget exact assertions.
- K04-A03: single end-to-end envelope; no actual proxy chain.
- K04-A04: dry-run/current-term precondition/idempotent apply; reversible external repair NOT implemented.
- K04-A05: unknown query, dedup and capacity; synthetic joint failure only.
- K04-A06: replayable evidence and explicit unverified real load.

Evidence lives in selfcheck-evidence.json. Public checks validate the declared slice, not every original acceptance criterion.

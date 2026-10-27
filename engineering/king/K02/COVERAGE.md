# Original acceptance coverage (partial, not full acceptance)

- K02-A01: four named logical projections; no external ownership system.
- K02-A02: receipt-only audit retention and tombstone; raw journal erasure NOT implemented.
- K02-A03: partial completion, retries and concurrent steps.
- K02-A04: stale/new writes blocked by persistent tombstone; no expiry.
- K02-A05: filtered logical restore per projection; no full backup restore engine.
- K02-A06: minimal proof output checked; source command journal may retain synthetic payload.

Evidence lives in selfcheck-evidence.json. Public checks validate the declared slice, not every original acceptance criterion.

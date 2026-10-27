# R03 — Transactional outbox lease fencing and retries

Repair the Java 21 in-memory outbox used by an order-credit service. Preserve the public `OutboxStore` and `Claim` API. No dependencies, network, wall-clock calls, or sleeps are needed. Inputs use explicit logical time (nonnegative milliseconds). This is an original local benchmark fixture, not a production persistence implementation.

## Contract
- `submit(id, amount)` atomically adds a positive amount to aggregate `total` and inserts one pending message. Nonblank IDs only. Duplicate IDs return false and have no effect, regardless of payload. Invalid input throws IllegalArgumentException without mutation.
- `claim(worker, now, lease)` returns the first eligible message in insertion order, or empty. Worker must be nonblank; lease must be positive. Pending messages are eligible at `due <= now`, with initial due zero. A claimed message is eligible for re-claim at `leaseUntil <= now`. SENT and DEAD are never eligible.
- Each claim/re-claim increments its message's attempt (first attempt 1) and obtains a globally unique increasing token. Lease end is `now + lease`. Overflow throws ArithmeticException before any mutation.
- `acknowledge(claim, now)` succeeds only for the current token AND worker on a currently CLAIMED message before its lease end; it transitions to SENT. Expired, forged, stale, or repeated acknowledgements return false without mutation.
- `fail(claim, now, backoff, maxAttempts)` uses the same ownership/lease conditions. A successful failure becomes DEAD when current attempts >= maxAttempts, otherwise PENDING until `now + backoff`. Nonnegative backoff and positive maxAttempts required; overflow throws ArithmeticException without mutation.
- Null claims and negative now are invalid. Failure argument validation occurs before ownership lookup. Claim fields attempt and leaseUntil are informational; ownership uses ID, worker and token against stored lease state.
- `total`, `size`, and `state` provide consistent snapshots; unknown ID state is MISSING. All operations must be thread-safe. Concurrent duplicate submissions must credit exactly once, and only one worker may own an unexpired claim.

Edit candidate `src/`. Evaluation is functional and public: verifier/reference in the benchmark repository are not secret tests. Do not inspect them during an agent attempt if measuring clean task performance. Local execution is NOT a secure sandbox for untrusted code.

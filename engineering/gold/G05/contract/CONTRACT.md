# G05 frozen executable slice contract v1

This is a public development fixture, not held-out acceptance. `modules/api`,
`modules/downstream`, `verifier`, and this contract are immutable during candidate
execution; hashes in `fixture-lock.json` detect accidental fixture changes.
The implementation owns only `Service` and delegates actual calls to `Callable`.

## Normative slice

1. Admission is bounded: slow-seat bulkhead has exactly 2 workers and 2 queued
   requests; independent-price bulkhead has exactly 1 worker and 2 queued requests.
2. A saturated bulkhead immediately throws `RejectedExecutionException`; no
   caller-runs policy, silent discard, unbounded queue or unbounded workers.
3. A caller never occupies a worker merely to wait for another task scheduled to
   that same pool. Return a future for the actual operation.
4. Successful values are unchanged and stable across repeated `get` calls.
5. Exceptions are propagated through the future, never converted to successes.
6. Deadline ownership belongs to the entry caller in this slice: at the deadline
   it calls `Future.cancel(true)`. The service must interrupt running downstream
   work, and cancellation of queued work must prevent the downstream invocation.
7. `SeatClient` owns a synthetic lease only while its call is active. Normal
   completion, interruption and shutdown release it exactly once in `finally`.
8. Cancelled queued work immediately frees its admission slot, even when both
   workers are blocked. Repeated cancellation cannot double count completion.
9. Saturating seat calls cannot prevent an admitted independent-price call.
10. Accepted work has exactly one terminal counter: completed, cancelled or failed.
    Counters may become visible after `get` returns, but must converge within the
    verifier's 2-second watchdog. Rejected submissions increment only rejection.
11. Shutdown interrupts active work, cancels every queued future, rejects new work,
    and joins workers. Running tasks interrupted by shutdown may count as failures
    or cancellations; queued work must report cancellation. Close is idempotent.
12. No assertion of starvation is based solely on elapsed time. `Incident` freezes
    two parents after they enqueue their children and before they wait: both worker
    slots are occupied, both children queued, zero free workers. This constructs the
    cyclic wait graph. Timed waits elsewhere are failure watchdogs, not performance
    claims or timing-based race proofs.

## Explicit non-goals / original-task gap

There is no HTTP request deadline parser, real connection pool, database, network
latency distribution, production SLA, load benchmark, distributed tracing system,
automated release gate or live rollback. Seat connection ownership is a local
resource probe; price independence is a separate local executor. Original catalog
acceptance requires engineering diagnosis/delivery beyond these tests. A green
slice is not full G05 readiness. Review the incident and operational deliverables
qualitatively; the runner does not grade prose.

## Invariant index

I01 worker budget; I02 queue budget; I03 seat result; I04 price result;
I05 actual two-worker concurrency; I06 price isolation during seat blockage;
I07 admission/rejection accounting; I08 deadline interruption/lease release;
I09 queued cancellation suppression; I10 cancellation capacity reclamation;
I11 exception accounting; I12 exact terminal accounting;
I13 shutdown queued-future cancellation and lease cleanup;
I14 post-shutdown rejection; I15 immutable completed results;
I16 admitted burst drainage and conservation.

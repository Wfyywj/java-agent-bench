# Reference delivery

Change: remove blocking parent tasks and return actual downstream futures; allocate
separate bounded executors for seat and independent price; abort on saturation;
remove cancelled queue entries; cancel drained futures on shutdown.

Mitigation: reject excess seat work rather than accepting unlimited queued demand.
Preserve price isolation and cancellation. Permanent fix breaks the wait edge,
not merely the thread count. Rollback to the original shared-pool PR is unsafe;
roll back to a previously verified bounded/isolation implementation or disable
booking admission while keeping the independent endpoint available.

Observe accepted/rejected/completed/cancelled/failed conservation, per-bulkhead
queue occupancy and active workers, connection leases and deadline cancellations.
No latency or throughput SLA is inferred from the watchdog. The budget 2+1 is a
fixture policy, not a production-sizing recommendation. No real deployment ran.

Cancellation is cooperative in Java. The synthetic downstream obeys interrupts;
clients ignoring interruption require transport deadlines and resource cleanup
outside this fixture. Core-worker counts are not live-worker leak metrics. The
runner uses process group kill as a last-resort timeout, not as evidence of clean
application lifecycle. Tests assert explicit close and lease cleanup first.

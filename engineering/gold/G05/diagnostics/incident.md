# Incident packet (synthetic, reproducible)

Entry path: caller -> Service.submit -> shared executor parent -> shared executor
child -> SeatClient.call. Parent synchronously waits in Future.get. With two
parents occupying two workers and two children queued, no child can start. Adding
a third worker only changes the load at which this recurs; an unbounded queue hides
rejection and cannot break the cycle. Slow seat requests additionally consume the
price endpoint's shared execution resource.

`bench.Incident` explicitly uses `parents`, `queued` and `allowWait` latches to
freeze the dependency graph. Its captured output is in each evidence run. The
reproducer does not depend on racing submissions, sleeps, or a guessed timeout.

Rejected alternative explanations: the controlled incident uses children that
return the constant 7 (no DNS, network, database or price calculation); it proves
executor starvation for this fixture, not that those factors are absent in a real
incident. Watchdogs are bounded waits to avoid hanging the verification process.

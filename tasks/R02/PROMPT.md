# R02 — Concurrent inventory reservations

Repair `src/Inventory.java` (and supporting source files if needed) without changing the public API. This service reserves units of a single SKU for checkout requests. No dependencies or persistence are required; correctness is within one JVM.

## Contract
- `new Inventory(capacity)` accepts zero or positive capacity; negative capacity throws `IllegalArgumentException`.
- `available()` returns the current free quantity.
- `reserve(id, quantity)` requires a non-null, nonblank id and positive quantity, otherwise throws `IllegalArgumentException` before changing state.
- A new id reserves exactly quantity units and returns an immutable ACTIVE `Reservation`. Insufficient stock returns `null` and does not bind that id.
- An existing id with the same quantity returns its current reservation snapshot without changing stock, including when available stock is zero. An existing id with different quantity throws `IllegalArgumentException`, including after cancellation.
- `cancel(id)` requires a non-null, nonblank id. It restores stock exactly once and returns true only on the ACTIVE → CANCELLED transition. Missing or already-cancelled ids return false.
- Cancellation permanently retains the id. Replaying it returns CANCELLED and never reserves again. Previously returned immutable snapshots do not change.
- All calls must be linearizable and safe under concurrent reserve/cancel/read calls. Stock must never be negative or exceed initial capacity.

Use Java 21 and the default package. Keep `Inventory` and `Reservation` public API compatible. Verifier and reference material are public in the benchmark repository; the prepared work directory omits them for clean task presentation, not secrecy. No model execution is part of this task.

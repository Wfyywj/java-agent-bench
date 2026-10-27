# Decisions

- All-or-nothing batch cancellation is fixed by S04-A01/A02, not inferred from a framework annotation.
- Checked BusinessFailure rolls back; runtime failure propagates and rolls back. No catch-and-success conversion.
- Already-cancelled batches are successful no-ops; delivered rows reject even if earlier rows were processed.
- Reserved inventory was subtracted before these operations. Delivery consumes that reservation; cancellation returns it exactly once.
- Batch-row locking is the chosen narrowed concurrency contract; inventory uses atomic arithmetic across batches.
- No user answers were fabricated. Original PostgreSQL + finite-pool requirements are not marked complete: this additional variant verifies real Spring/H2 only.

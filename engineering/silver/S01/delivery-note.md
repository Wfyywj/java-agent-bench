# Delivery and rollback

Signed refund callback CLI, atomic persisted event receipts and billing projection; fault injection before commit and after commit with restart replay.

Use a fresh temporary data directory for each test. To restore a demo, stop the process and delete only its explicitly supplied test data directory, then rerun init/load. Do not replace production data or replay payment operations. Schema rollback proposals are design instructions, not executed migrations.

Residual limits: No HTTP adapter, real payment dispatch, database transaction engine, distributed delivery, fsync/power-loss guarantees, or production secrets.

Do not infer catalog readiness, model capability, hidden evaluation quality or production safety from these public development checks.

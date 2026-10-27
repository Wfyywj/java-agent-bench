# Delivery
Scope: local single-writer Java REST service; no framework/database installation. Fix checks persistent replay before lifecycle validation, rejects changed payloads, serializes concurrent requests and publishes one staged snapshot.

Rollback: stop the service, retain its state snapshot, restore the prior code only after evaluating the known duplicate-return risk. Do not blindly replay stored successful returns or discard event history. Restore a saved snapshot only in this synthetic environment, never as an implied production repair procedure.

Residual risks: file rename is not a PostgreSQL transaction, no fsync/power-loss guarantee, no multi-process writer locking. Tenant is an explicit synthetic request field rather than real authentication. Fault header is a local test hook, not suitable for exposed deployment. Public tests cannot establish unseen model generalization; no scores are claimed.

# Delivery and rollback

File-backed async export command flow with create/worker/download authorization, revoked membership, explicit job scope on reused worker instance, expiry, safe synthetic CSV columns.

Use a fresh temporary data directory for each test. To restore a demo, stop the process and delete only its explicitly supplied test data directory, then rerun init/load. Do not replace production data or replay payment operations. Schema rollback proposals are design instructions, not executed migrations.

Residual limits: CLI rather than REST/object-store URLs; principal is trusted adapter input, not authentication. No real object-storage signing, HTTP non-enumeration policy, cross-process worker pool or external IAM.

Do not infer catalog readiness, model capability, hidden evaluation quality or production safety from these public development checks.

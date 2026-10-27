# Delivery and rollback

Independently compiled SDK/gateway/service module snapshots with old/new request matrix, dual-write downgrade, list precedence and authoritative server entitlements.

Use a fresh temporary data directory for each test. To restore a demo, stop the process and delete only its explicitly supplied test data directory, then rerun init/load. Do not replace production data or replay payment operations. Schema rollback proposals are design instructions, not executed migrations.

Residual limits: No real separate Git histories, remote HTTP schemas, generated client runtime, deployed telemetry, or rolling production experiment.

Do not infer catalog readiness, model capability, hidden evaluation quality or production safety from these public development checks.

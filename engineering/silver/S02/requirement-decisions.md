# Frozen synthetic fixture decisions

New explicit eligibilityCodes wins even when empty; omitted (~) falls back to legacy level. Lists accept MEMBER/STUDENT, select an owned STUDENT first then MEMBER. Unknown codes fail 422. New SDK dual-writes level; new-only calls downgrade to NONE on old service. Client claims never create server entitlement.

Pending: No real separate Git histories, remote HTTP schemas, generated client runtime, deployed telemetry, or rolling production experiment.

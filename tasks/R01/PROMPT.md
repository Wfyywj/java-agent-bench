# R01 — Tenant-scoped payment idempotency

Fix `PaymentService` and supporting production code for an in-memory checkout service. Preserve the public API. Each service instance owns its idempotency history. Pass the exact tenant, payload, and amount unchanged to the gateway; return the gateway-provided receipt unchanged (including opaque transaction ID and amount), not a reconstructed request receipt.

`pay(tenant, key, payload, amount)` must call `Gateway.charge` at most once for a **successful** operation with the same `(tenant, key)` and return the original receipt on replay. A replay must have exactly the same payload string and amount; otherwise throw `IllegalStateException` before touching the gateway. Different tenants may use the same key independently. Treat tenant and key as separate strings (concatenating with a delimiter is not collision-safe).

Reject null or blank tenant, key, and payload, and nonpositive amounts with `IllegalArgumentException` before any side effect. Do not trim or otherwise normalize valid identifiers/payloads. Gateway exceptions propagate and must not poison a key: a later attempt may succeed, even with changed payload. Concurrent calls must have linearizable behavior: duplicate successful requests get the same receipt, and conflicting requests cannot both charge. No external database/network is required. Global serialization inside one instance is acceptable.

This is a local functional exercise, not a secure sandbox. The repository's verifier and reference are public, not hidden tests. Do not change verifier files.

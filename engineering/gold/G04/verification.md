# Executed verification

Reference: INVARIANTS=22 FAILURES=0; three fresh compile/workdir repeats.
All 6 negative variants rejected behaviorally in each repeat; compilation failure never counts as mutation detection.

| Variant | Results over three runs |
|---|---|
| reference | PASS x3 |
| baseline | REJECT x3: FAIL cross tenant isolation; FAIL exact authority calls including failed read; FAIL six distinct authority misses counted |
| mutant_tenant_key | REJECT x3: FAIL cross tenant isolation; FAIL exact authority calls including failed read; FAIL six distinct authority misses counted |
| mutant_stale_on_error | REJECT x3: FAIL expired grant fails closed on outage |
| mutant_long_ttl | REJECT x3: FAIL exact authority calls including failed read; FAIL expired grant fails closed on outage; FAIL lost invalidation converges at TTL; FAIL negative cache bounded |
| mutant_default_allow | REJECT x3: FAIL cross action isolation; FAIL cross resource isolation; FAIL cross subject isolation; FAIL cross tenant isolation; FAIL second caller cannot borrow read |
| mutant_hidden_call_count | REJECT x3: FAIL exact authority calls including failed read; FAIL six distinct authority misses counted |

## Counter oracle correction
Relative before/after call-counter assertions alone allowed a constant-zero diagnostic counter. Absolute externally counted misses (6 and 13) now check authority telemetry; mutant_hidden_call_count is retained.

Full evidence: verification-results.json. Public development checks only; no hidden holdout or production integration claim.

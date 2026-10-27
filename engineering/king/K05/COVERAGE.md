# Original acceptance coverage (partial, not full acceptance)

- K05-A01: synthetic policy gate and cutoff; fee amount out of scope.
- K05-A02: per-item refund limit, concurrent refunds, exact conserved totals.
- K05-A03: version gating and rollback order; no real cross-repo serializers.
- K05-A04: starter and three mutants reproduce defects; no human review scoring.
- K05-A05: persistent pending state, repeat settle/reconcile; no actual provider call.
- K05-A06: scripted phase history; no production metrics/canary population.

Evidence lives in selfcheck-evidence.json. Public checks validate the declared slice, not every original acceptance criterion.

## Independent audit hardening
A token payload omitting item identity previously survived same-item checks. Added two distinct orders, equal-amount cross-item token conflict, unchanged conservation after conflict, valid original replay, independent second-item refund and final settlement conservation. The new semantic mutant must fail.

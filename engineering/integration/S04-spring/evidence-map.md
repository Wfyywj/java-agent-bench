# Evidence map

| Original acceptance | Independent verifier checks |
|---|---|
| A01 atomic boundary | spring-proxy; active-transaction-at-repository; successful-cancel-atomic-state |
| A02 all rollback | checked-mid-batch-rollback; runtime-mid-batch-rollback; late-checked-failure-rollback |
| A03 repeat/delivered | repeat-cancel-idempotent; mixed-cancelled-pending-processes-remainder; mixed-cancelled-delivered-still-rejects; mixed-cancelled-pending-failure-rolls-back; delivered-order-blocks-whole-batch; delivery-and-repeat-no-release; mixed-delivered-pending-delivers-remainder; mixed-delivered-cancelled-rejects-delivery |
| A04 concurrency | cancel-wins-concurrent-delivery; delivery-wins-concurrent-cancel; concurrent-distinct-batches-no-lost-update |
| A05 real proxy failures | spring-proxy; active-transaction-at-repository; three mid-batch failure tests |
| Narrow lock scope | batch-row-lock-visible-to-independent-connection; unrelated-batch-not-globally-locked; unrelated-batch-preserved |

Baseline compiling and failing active-transaction/SQL rollback rules rules out missing dependency or syntax errors as its failure explanation. The default-checked-policy mutant has a real active proxy transaction but commits on checked failure, distinguishing proxy setup from rollback configuration. Lost-update mutant fails direct stock equality under a forced stale-read schedule. Evaluator source is separately staged; no reference class is present in candidate runtime.

Independent audit initially found an accepted `continue` → `return` counterexample at a cancelled prefix. Added three cancellation mixed-state tests and two analogous delivery tests, plus both early-return mutants. `evidence/audit-counterexample.json` records the now-rejected candidate; this is a verifier coverage improvement, not a reference behavior change.

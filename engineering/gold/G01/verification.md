# Executed verification

Reference: INVARIANTS=16 FAILURES=0; repeated three times with fresh compile and working directory.
Baseline and four named semantic mutants rejected in all three repeats. No compile failures counted as successful mutant detection.

| Variant | Results over three runs |
|---|---|
| reference | PASS x3 |
| baseline | REJECT x3: FAIL recovery audit; FAIL repeat recovery no audit duplication; FAIL restart recovery durably releases |
| mutant_missing_intent | REJECT x3: FAIL recovery audit; FAIL repeat recovery no audit duplication; FAIL restart recovery durably releases |
| mutant_wrong_key | REJECT x3: FAIL key bound to lease; FAIL key bound to tenant |
| mutant_overlap | REJECT x3: exception on violated contract |
| mutant_release_noop | REJECT x3: FAIL restart recovery durably releases |

Machine-readable full evidence: `verification-results.json`. These are public development tests, not a hidden holdout or model evaluation. See CONTRACT.md and task.json for unimplemented original acceptance requirements.

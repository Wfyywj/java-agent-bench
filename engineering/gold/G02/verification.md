# Executed verification

Reference: INVARIANTS=22 FAILURES=0; repeated three times with fresh compile and working directory.
Baseline and four named semantic mutants rejected in all three repeats. No compile failures counted as successful mutant detection.

| Variant | Results over three runs |
|---|---|
| reference | PASS x3 |
| baseline | REJECT x3: FAIL published version immutable |
| mutant_mutable_versions | REJECT x3: FAIL published version immutable |
| mutant_floor_minutes | REJECT x3: FAIL ceil minute after free |
| mutant_latest_publication | REJECT x3: FAIL publish not effective |
| mutant_zero_amount | REJECT x3: FAIL bill snapshot v1; FAIL ceil minute after free; FAIL daily cap; FAIL diff before after; FAIL fall DST elapsed 25h; FAIL history not overwritten; FAIL midnight split cap; FAIL spring DST elapsed 23h |

Machine-readable full evidence: `verification-results.json`. These are public development tests, not a hidden holdout or model evaluation. See CONTRACT.md and task.json for unimplemented original acceptance requirements.

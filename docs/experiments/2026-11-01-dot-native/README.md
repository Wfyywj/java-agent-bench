# dot-native exploratory comparison — November 1, 2026

## Result
One B02 smoke passed 10/10, excluded from comparison. All 12 planned attempts completed. Raw verifier full-task outcomes: 6 passed, 6 failed; no retries or missing slots.

| Task | No skill, repeats 1/2/3 | Workflow, repeats 1/2/3 |
|---|---|---|
| B02 | 10/10, 10/10, 10/10 | 10/10, 10/10, 10/10 |
| S01 | 14/16, 8/16, 10/16 | 14/16, 14/16, 10/16 |

These are frozen verifier compatibility outcomes, NOT evidence that the workflow improves business correctness. Raw results have not been rescored.

## Independent adjudication
S01 failures concentrate on underspecified response/receipt policy:
- Sequence 1 stale receipts reused with another payload: candidates return conflict while verifier expects stale; the public same-sequence/different-body rule supports a conflicting interpretation.
- New-sequence same-terminal updates: candidates return applied while verifier expects stale. The prompt does not specify these response labels; starter code used applied.
- Repeat-2 control additionally returns applied for protected processing/cancelled updates while preserving the terminal projection.
Some intended later assertions were not reached because fixture setup failed first. Their outcomes remain unverified. No demonstrated monetary-state correctness uplift follows from these check-count differences.

Workflow artifacts exist and were independently inspected, but stage documents alone are not proof of complete execution, independent review or actual sequential orchestration.

## Next action
Clarify the transition/receipt/response matrix and split setup assertions from target assertions. Version a new task/verifier contract, then run a new comparison. Preserve this run unchanged; do not retroactively turn ambiguous failures into passes.

## Evidence
Download dot-native-evidence.zip and inspect comparison/plan.json, starts/, records/, operator/, audits/, operator-notes/ and separate smoke/. The publication manifest maps original and public SHA256 values: copies are byte-identical. Opaque execution workspace paths are provenance, not downloadable links. display.json evidence paths are relative to comparison/ INSIDE the archive; do not auto-fetch them as web URLs.

All 12 records validated against the frozen plan and runner. ZIP entries were byte-compared to source files. Credential-pattern scan found no keys/tokens; files were reviewed as public task code and operator evidence. No private conversation transcript or credentials are intentionally included.

Frozen plan: 9f882dba01fa6588add61b3164ac52a0328917d43f6dc88c2ff2e67fc0c6b50a.
Implementation: remote 83c3d711e223789c1508c6edfd1ab6ada503d601, local 5a583b79b9268035da298c1d47a924e30d22ec94; identical Git tree d62b1cfff1a5cf86aa559048cd1c6ce31c175a0e.
Skill revision: 80e15acdf61d2cecf1ff79e9088a8149e64ffc1a.
Schema: experiment_tools/dot-native-results-1.0.schema.json at implementation commit.

## Limits
Actual dot-agent outputs; backend model/version/usage/cost unknown. Fresh no-history conversations, shared filesystem with instruction-only boundaries, public tasks, unsigned operator observations, source inspection before local execution. Not a secure sandbox or a named-model ranking. Timing includes dispatch, parent observation and shared CPU contention, so is not a model-speed benchmark. Per-attempt 900-second cancellation is best effort. Environment clarifications and unequal interactions are preserved in operator-notes. Small sample; no causal efficacy or significance claim. Strict CLI pilot remains unchanged. No frontend deployment.

# Source-bound trusted-fixture gates

Run `python3 scripts/check_engineering.py --m1`. This runs checked-in trusted
fixtures, not agents, model trials, or hostile submissions. No secure sandbox
is claimed.

## Current selection and history

Each invocation acquires an exclusive nonblocking `.run.lock`, allocates a
unique run ID, durably writes `runs/<run_id>/attempt.json`, then atomically
publishes `latest.json` with state `running` **before** source hashing or process
launch. A competing invocation exits unsuccessfully without replacing the
active selection. SIGKILL/power loss may leave `running`; it is explicitly not
a successful current result.

On completion, each task and a summary are saved under the independent run
directory. Even missing Java, collector exceptions, cancellation, missing reports
and invalid evidence create failure records. `attempt.json` becomes terminal;
`latest.json` selects `completed` or `verification_failed`. Atomic writes fsync
the file and parent directory. The legacy per-task `m1-four-gates.json` and
summary paths are compatibility snapshots of the same attempt, not historical
selectors. Pre-migration snapshots are copied once to `evidence/legacy/` before
replacement; prior run directories are never deleted or overwritten by another
invocation.

The discovery builder reads only the selected completed run, validates its
identity and compatibility snapshots, and compares each task's current source
fingerprint. A missing binding/changed bundle yields `gate_status: stale`;
a running, failed or unreadable selection yields `verification_failed`. Neither
can promote `gates_green`; the implementation remains an honest runnable slice.
A failed overall attempt is conservative: no task from it promotes. The builder
also removes stale derived design links. Re-running after repair creates a new
attempt without deleting the failed one.

## Fingerprint boundary

`sha256-source-bundle/v1` hashes a canonical sorted list of relative file paths
and per-file SHA-256 hashes. It includes the entire task tree (manifest,
whitelist, prompt, reference, baseline, verifier, mutants, dependency locks,
fixtures and evidence **inputs**, including B02 seed/schema), shared `scripts`,
`harness`, `engineering_tools` if present, `schemas`, tier-level Python helpers,
and root dependency configurations. Added/deleted/renamed inputs change it.
Symlinks fail closed. Known generated selfcheck/M1 reports, bytecode, cache and
build directories are excluded; other inputs are included conservatively.
Fingerprints are checked before and after collection, so changes during a run
cannot produce green evidence. They are content bindings, not signatures or a
claim of adversarial tamper resistance. Java/Python/platform information is
recorded separately in the run environment; timestamps do not enter source hash.

## Mutant outcome contract

Only `semantic_assertion` with nonempty named `failed_assertions` counts as a
kill. Every required repeat must fail semantically. `survived`, `timeout`,
`compile_error`, `startup_error`, `infrastructure_error` and `missing_report`
are separate outcomes, never substitute kills. A nonzero process exit alone is
insufficient. Verifier wrappers emit `FAIL` only for assertions and `ERROR` for
other exceptions. Mixed assertions plus infrastructure errors fail closed.
Silver comparisons with errored steps do not count as semantic failures.
The persisted shape is documented in `schemas/m1-evidence.schema.json` and
validated more strictly by the gate/catalog code.

Regression command (no Java/models for integrity tests):

```sh
python3 -m unittest discover -s tests -p test_m1_evidence_integrity.py -v
```

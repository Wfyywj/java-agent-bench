# S03 engineering slice

File-backed async export command flow with create/worker/download authorization, revoked membership, explicit job scope on reused worker instance, expiry, safe synthetic CSV columns.

**Not full-catalog ready.** CLI rather than REST/object-store URLs; principal is trusted adapter input, not authentication. No real object-storage signing, HTTP non-enumeration policy, cross-process worker pool or external IAM.

- Selfcheck: `python3 run_selfcheck.py` (baseline must fail; reference must pass 3 runs; all compiling mutants must be killed).
- Candidate: `python3 run_selfcheck.py --candidate ABS_PACKAGE` (JSON, exit 0 only on all behavioral checks).
- 12 public black-box scenarios. Oracle owns fixed expected outputs / independently computed relational sets, not reference-generated answers.
- Source snapshots: `baseline/src`, `reference/src`, `mutants/*/src`.
- Exact original contract: `original-task.json`; explicit narrowed scope: `task.json`.
- Evidence: `evidence/selfcheck.json`, including actual command traces, per-variant source digest, compile errors if any and residual limits.

The CLI uses status-like strings but is not HTTP. Clean temporary data directories are recreated for every scenario and run; Candidate runtime heaps are 128 MiB (compiler uses the host JVM default), per-command timeout 15 s, compiler timeout 45 s, combined output limit 128 KiB. JDK 21 target/source are explicit because this runtime lacks release-symbol metadata. No wall-clock speed claims or benchmarked model rankings.

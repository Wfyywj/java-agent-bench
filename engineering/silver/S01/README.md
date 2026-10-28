# S01 engineering slice

Signed refund callback CLI, atomic persisted event receipts and billing projection; fault injection before commit and after commit with restart replay.

**Not full-catalog ready.** No HTTP adapter, real payment dispatch, database transaction engine, distributed delivery, fsync/power-loss guarantees, or production secrets.

- Selfcheck: `python3 run_selfcheck.py` (baseline must fail; reference must pass 3 runs; all compiling mutants must be killed).
- Candidate: `python3 run_selfcheck.py --candidate ABS_PACKAGE` (JSON, exit 0 only on all behavioral checks).
- 16 public black-box scenarios. Oracle owns fixed expected outputs / independently computed relational sets, not reference-generated answers.
- Source snapshots: `baseline/src`, `reference/src`, `mutants/*/src`.
- Exact original contract: `original-task.json`; explicit narrowed scope: `task.json`.
- Evidence: `evidence/selfcheck.json`, including actual command traces, per-variant source digest, compile errors if any and residual limits.

The CLI uses status-like strings but is not HTTP. Clean temporary data directories are recreated for every scenario and run; Candidate runtime heaps are 128 MiB (compiler uses the host JVM default), per-command timeout 15 s, compiler timeout 45 s, combined output limit 128 KiB. JDK 21 target/source are explicit because this runtime lacks release-symbol metadata. No wall-clock speed claims or benchmarked model rankings.

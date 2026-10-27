# King engineering slices (K01–K05)

Five original Java 21 multi-file command services exercise durable journal replay and domain-specific staged recovery. Run `python3 engineering/king/run_all.py` for three reference/starter/semantic-mutant repetitions per task. Or use `K01/run_selfcheck.py --candidate /absolute/submission` (the package must contain src/).

| Task | Realized slice |
|---|---|
| K01 | Fenced entitlement grants, failover, response-loss replay, term-increasing rollback |
| K02 | Versioned deletion manifest, four projections, retained receipt, filtered restore |
| K03 | Independent integer differential oracle, approved correction, pinned billing and tenant-period cutover |
| K04 | Connection-term recovery, shared retry budget, admission, durable dedup, repair dry-run |
| K05 | Per-item refund conservation, pending settlement reconciliation, phased version compatibility |

Each task has PROMPT.md, PHASES.md, task.json with original catalog criteria and explicit exclusions, baseline/src, reference/src, public mutants.json, agent-files.json submission whitelist, and selfcheck-evidence.json. Shared verify.py is an independent Python black-box verifier: exact outputs, restart reconstruction, conservation, rejection behavior, and torn-log fail-closed checks. No candidate success flags are trusted.

The runner compiles via `java -m jdk.compiler/com.sun.tools.javac.Main -source 21 -target 21` because this environment's stripped JDK lacks --release metadata. Runtime processes use -Xmx64m; compiler timeout 30 seconds, invocation timeout 15 seconds, captured output limit 64 KiB, source limit 1 MiB in candidate mode, clean temporary workspaces. These are operational limits, **not a secure sandbox**. Only run trusted local candidate code.

All tests, references and mutants are public development assets. No held-out evaluation, model call, calibrated difficulty, production cluster, production load or legal compliance claim. The catalog design remains broader than these runnable_slice implementations. Synthetic data only.

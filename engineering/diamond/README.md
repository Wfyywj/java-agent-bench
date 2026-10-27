# Diamond engineering slices

D01–D05 retain exact original catalog contracts in task.json, but status is **runnable_slice**, not catalog-complete or difficulty-calibrated.

Run each `python3 D01/run_selfcheck.py`; submit arbitrary trusted code with `--candidate /absolute/package` (src/Main.java). No model calls, installs, dependencies or network. Java21 stdlib only, compiler module command. Original fixtures and public independent verification. Three repeats of reference, baseline and three mutants are evidence, not model performance.

D02 additionally evaluates agent-authored legal test histories with `python3 D02/verifier/evaluate_suite.py /absolute/suite.json`; emits per-history detection matrix and causal-precondition-preserving deletion-1-minimal failures.

File-backed atomic replacements establish process-restart semantics only; audit append is not atomic with snapshot commit and no power-failure durability claim is made. Local timeout runner is not a security sandbox. D04 rejects arbitrary Java plugins rather than claiming unsafe classloader isolation.

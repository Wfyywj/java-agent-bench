# Reproducible local Java evaluation kernel

Requirements: Python 3.10+ and Java 21+ with the `jdk.compiler` module. No Maven, Gradle, dependency downloads, network requests, API keys, or model calls. When `javac` is not installed as a command, the harness invokes the compiler module directly.

From the repository root:

```sh
python3 harness/bench.py validate-task R01
python3 harness/bench.py prepare R01 /tmp/r01-agent-work
# An authorized human/agent edits ONLY /tmp/r01-agent-work/src/*.java.
python3 harness/bench.py evaluate R01 /tmp/r01-agent-work/src --output /tmp/r01-result.json
python3 harness/bench.py selfcheck R01 --output /tmp/r01-selfcheck.json
python3 harness/bench.py selfcheck R02
python3 harness/bench.py selfcheck R03
python3 -m unittest discover -s tests -v
```

`R01`, `R02`, and `R03` are original **runnable** fixtures, separate from design-only catalog entries. They exercise in-memory business contracts, not real production services. The flawed candidate is a calibration baseline, **not an evaluated AI model**. Reference implementations are independently authored solutions to the contracts. A `selfcheck` succeeds only when baseline code compiles but fails a behavioral check, the reference passes every check, and a targeted compiling reference mutation fails a behavioral check. R01 has three targeted mutations, R02 has two, and R03 has four, including independent audit regressions. This is not comprehensive mutation coverage.

Each evaluator invocation copies candidate `.java` files and the public verifier into a fresh temporary build directory, disables annotation processing, compiles, runs, and removes the build directory. Existing `.class` files are never reused. Compilation and execution each have a configurable wall-clock timeout (20 seconds default; at most 300); ordinary child process groups are killed on timeout. Java execution has a 256 MiB heap limit. Combined stdout/stderr capture is bounded to 1 MiB per phase while streaming; exceeding the limit kills the process group and reports a distinct output-limit status. Exit code 0 means success, 1 means a measured failure, 2 means invalid input or an infrastructure error. Compile failure and timeout remain distinct from functional failure. JSON includes per-check outcomes, task version, SHA-256 of the normalized unified source diff from baseline, timestamp, Java/Python/OS information, command logs, and status. A no-change baseline patch hashes the empty diff; hashes are patch identities, not task identities. The JSON schema describes individual evaluation results; selfcheck results wrap baseline/reference results plus a mutation-result array (and retain the first mutation in a compatibility field).

## Integrity boundaries — read before running candidates

**This is local functional evaluation, NOT a secure sandbox. Run only trusted code.** Java candidates execute with the invoking account's filesystem and network privileges. Path traversal and source symlink guards, argument-list process execution (never `shell=True`), clean builds, timeouts, and heap limits reduce accidental failures; they do not contain hostile code. Candidate code could read the repository, tamper with files, forge verifier output, or use native/process/network capabilities. This harness does not enforce CPU, disk, network, or process-count isolation. The output cap only bounds captured pipe output, not writes to other files or escaped processes. Do not use it to execute arbitrary downloaded code or arbitrary model-generated submissions without a separate hardened runner.

`prepare` copies only source, prompt, and task metadata. It omits verifiers, mutation recipes, and reference source **from that workspace**, but the originals remain public in this repository. They are not hidden or secret tests. Sanitization is a convenience, not isolation or leakage prevention. A serious benchmark deployment needs separately hosted private tests, disjoint agent/evaluator filesystems, network-off ephemeral containers/VMs, resource quotas, immutable verifiers, trusted result transport, provenance tracking, and human review of suspicious outcomes. See [the future runner integrity protocol](INTEGRITY.md).

Tests check baseline/reference/mutation behavior and basic harness contracts. They do not prove broad coverage, generalization, production readiness, model ranking, or security containment. No model scores are fabricated or implied by these fixture measurements.

# Candidate task: recover the booking gateway under bounded concurrency

The candidate PR in `baseline/src/bench/Service.java` reuses the entry executor
for seat-client work. Operators report booking timeouts during seat latency while
price endpoints are also degraded. Budget increases and unbounded queues are not
approved. Repair the implementation without changing `Gateway` or test fixtures.

In a staged candidate package, run `python3 run_selfcheck.py --candidate "$PWD"`
for JSON public feedback (exit 0 iff passing). In the original development task
folder, use `python3 run_selfcheck.py --candidate "$PWD/baseline"` instead.
The implementation package must contain `src/bench/Service.java`.
The reference and mutants are disclosed development calibration material; they
must be excluded from any genuine held-out candidate package.

Deliver:
- the scoped implementation patch;
- `diagnosis.md` with a wait graph, code path and alternatives ruled out;
- regression cases linked to I01-I16, distinguishing watchdogs from race proofs;
- `delivery-note.md` with mitigation, rollback, monitored counters and unverified
  factors. Do not claim real database or HTTP acceptance or a production throughput
  result from this local fixture.

Use `contract/CONTRACT.md` as the normative slice, not the reference source.
All records and client behavior are synthetic. No models, package installation,
external network or real credentials are necessary. Do not edit fixture hashes,
contract, modules or verifier to make a candidate pass.

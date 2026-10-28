# Strict concurrency failure boundaries

The selfcheck still requires each negative control to compile, finish all 20
checks, exit 1, contain at least one explicit `FAIL`, and contain no `ERROR`.
Compile failures, incomplete runs, generic SQL/runtime failures and process
errors are not semantic kills.

The concurrency oracle preserves these narrow business assertions:

- `workerResult` unwraps a worker's `AssertionError` through executor/completion
  wrappers. It does not reclassify other worker exceptions.
- `orderedResult`, used only for the two ordered terminal races, recognizes the
  frozen repository guard `IllegalStateException("Concurrent order transition")`
  as a violation of required per-batch serialization. Other runtime and SQL
  failures remain errors. This recognizes the repository contract, not a mutant
  name or candidate identity.
- Only the unrelated-batch progress probe turns its own two-second wait expiry
  into an assertion: the first batch is deliberately held while an unrelated
  batch must finish. Other wait expiries remain errors. As already documented,
  this bounded-progress check may require calibration on overloaded machines.

`tests/test_spring_contract_boundaries.py` compiles a Java helper probe using the
frozen dependency cache and proves both recognized assertions and preservation
of unknown runtime, SQL, wrapped SQL, and timeout failures. Full trusted fixture
selfcheck remains necessary to establish all ten seeded negative controls.

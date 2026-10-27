# B02 · Campus equipment returns

You maintain a small Java return service. A cabinet retries after a lost HTTP response; operations reports two cleaning jobs for one loan. Repair `baseline/src`, preserve the public API, and add regression tests. Inspect `evidence/incident.log`, `seed.tsv`, the planned SQL schema, and the repository/service boundary before choosing a fix.

## Frozen business contract
- `POST /returns`: URL-encoded `tenant`, `loan`, `token`, `equipment`, `damaged=true|false`; successful responses are `200 loan=<id>;state=CLEANING|REVIEW`.
- A token is scoped to its tenant and binds the loan, equipment and damage flag. Exact replay returns the original response, including after process restart, without another event or job. A changed payload is `409 TOKEN_CONFLICT`.
- Tenant/unknown-loan failures have indistinguishable `404 NOT_FOUND` responses. An unborrowed/retired item, or equipment that is not the loan's equipment, yields `409 NOT_RETURNABLE`.
- A normal return enters CLEANING with one job; damaged returns enter REVIEW, have no cleaning job and never become available automatically.
- Loan state, event and cleaning job publish atomically. Local test header `X-Test-Fault: 1|2|3` injects failure after each staged write. Failure must return `503 RETRY_LATER` with no effects, and retry must work.
- Two independent HTTP connections may submit concurrently. There is one process/writer in this adapter. Do not replace durability with an in-memory replay cache.

## Required delivery
Submit `requirement-decisions.md`, `evidence-map.md`, scoped Java changes, `regression-tests/` mapped to B02-A01…A05, and `delivery-note.md` with rollback and unverified items. Distinguish the provided business answers from your assumptions. Do not change verifier or reference to make a candidate pass.

## Running
`python3 run_selfcheck.py` compiles the starter, reference and diagnostic semantic mutants in fresh temporary directories and runs HTTP checks. For candidate evaluation use the documented verifier against your compiled classes. Java 21 and Python 3 standard library only; no dependencies are downloaded.

## Honest scope
This package implements the B02 business workflow using a durable file snapshot adapter so it runs offline. It does **not** execute PostgreSQL, two database connections, SQL unique constraints, crash-durability/fsync, or multi-process locking. B02-A03 and A05 therefore have local-adapter evidence, not full catalog infrastructure acceptance. `evidence/schema.sql` is design evidence only. All evidence is synthetic/public; these are development fixtures, not hidden tests or model scores. The runner is not a secure sandbox; run only trusted code in a separate restricted execution environment.

## Prepared workspace layout
The sanitized presentation copy contains `src/` (from repository `baseline/src/`), the prompt, task metadata, and the explicitly listed public input files under `evidence/`. It does not include the local evaluator, reference answers, verdict/diagnosis contracts, or selfcheck results. Run evaluation commands from the benchmark repository, passing this package root with `--candidate`. The original repository remains public; this is presentation separation, not a hidden or secure evaluation.

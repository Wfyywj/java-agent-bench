# Bronze integrity audit — v0.1.1

Independent local audit, 2026-10-27. No model calls or external publication. These are public trusted-code development fixtures, not hidden tests or secure sandboxes.

## Reproduced defects and fixes

| Task | Previously compiling false positive | Correction |
|---|---|---|
| B01 | Replace persisted supplied `note` with `""`; all 16 behavior assertions and CLI/decisions passed. | Check a nonempty note round-trip exactly. Persistent `dropped_note` semantic mutant; 17 behavior assertions. |
| B02 | Execute `next.loans.put(...)` only for damaged returns; normal loan stays BORROWED, while all eight HTTP groups passed. | Independently check normal state on disk and after restart, reject another token for the returned loan, check concurrent normal state. Persistent `normal_loan_state_omitted` mutant. |
| B03 | Raise accepted maximum page limit from 100 to 100000; all five groups passed. | Test invalid limits 0, -1, 101, 100000, nonnumeric input, plus valid 1/100. Persistent `limit_oversized` mutant; six groups. |
| B05 | Replace serialized CSV row with `CORRUPTED`; all 27 assertions passed. | Independent committed-output parser checks header, record values, commas and doubled quotes. Reference now preserves the specified header. Persistent corrupted-output and missing-header mutants; 28 assertions. |

B05's output oracle does not call the candidate parser/encoder. A differently quoted but semantically equivalent implementation was separately executed and passed 28/28, avoiding a reference-format-only gate.

## Candidate protocols

All five now accept `--candidate /absolute/package` with `src/` where code is part of the task. B03 retains explicit `--candidate-src` as a legacy interface. B04 is a review task: it evaluates `review.json`, does not compile submitted source, and does not require repairing the reviewed PR. Invalid B02/B04 inputs exit 2; measured candidate failure exits 1. Individual task report shapes are not the R-series result schema.

B04 also rejects blockers incorrectly hidden among nonblocking suggestions. Candidate protocol tests prove an otherwise valid review is accepted even with deliberately uncompilable submitted source.

`agent-files.json` is an exact source/target whitelist for every Bronze package. Only baseline, prompt, task metadata, and named public input fixtures are copied. Required input fixtures are explicitly staged under `public-inputs/` and mapped to the prompt's `evidence/` names; evaluator results, reference answers, frozen contracts, and verifier code are excluded. The original repository remains public, so this is clean presentation, not leakage resistance.

## Evidence and limits

Each task was rerun twice with byte-identical selfcheck JSON; see task-local `evidence/audit-repeatability.json`. Reference variants pass, baseline variants fail, and all 25 selfcheck negative controls are rejected. A control may be a Java mutation or structured-decision/review mutation; do not label all 25 as Java mutations.

Executable protocol regressions: `python3 -m unittest discover -s tests -p 'test_bronze_protocol.py' -v`.

Scope remains explicit: B02 is a file adapter, not PostgreSQL; B03 does not establish production authorization or SQL plans; B04 checks public structured review anchors, not arbitrary prose; B05 uses deterministic stream/temp-file resource oracles, not production DB exhaustion. No broader completeness, model ranking, or hostile-code isolation is established by these checks.

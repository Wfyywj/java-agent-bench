# Bronze engineering development packages

Five original, multi-file Java 21 engineering fixtures derived from catalog B01–B05; these are distinct from the compact R-task lane. They use real CLI/filesystem or loopback HTTP entrypoints, intentional baseline defects, corrected reference sources, independent business assertions, and semantic mutants.

Run all: `python3 engineering/bronze/run_all.py` from repository root. Each task also has `run_selfcheck.py`; consult its prompt and task.json for its candidate protocol. Requires Python 3 and Java 21 with jdk.compiler. No installation, downloaded dependencies or network service is required (B02/B03 bind loopback).

| Task | Engineering surface | Honest scope boundary |
|---|---|---|
| B01 | Configured scheduler, Clock, persisted booking repository, CLI, frozen clarification contract | HTTP-compatible result value, not live HTTP adapter; prose not automatically graded |
| B02 | Equipment-return REST, durable atomic file replacement, concurrent requests, restart and fault hooks | NOT PostgreSQL transactions, SQL uniqueness or two DB connections |
| B03 | REST keyset paging over 44 real CSV rows, context-bound tokens and live dataset changes | File repository, not SQL query plans; tenant parameter is not production auth |
| B04 | Multi-file pricing PR, independently frozen review verdict, Decimal oracle and corrected code | Structured review checks, not LLM-only prose judging or permission to patch during review |
| B05 | CSV importer, tracked stream/temp resource lifecycle, diagnosis artifacts | Synthetic incident evidence; no real DB exhaustion; single-physical-line CSV records |

Public development fixtures only. Reference answers and verifiers are exposed; package delivery for a future held-out evaluation must separate them. These runners are **not secure sandboxes** and must execute trusted code only. No model evaluations, model scores, difficulty calibration, real production recovery or production readiness is claimed. Central catalog statuses are deliberately untouched; especially B02 infrastructure remains a partial adapter realization.

Acceptance criteria are copied verbatim in each task manifest; check coverage and exclusions alongside them. Baseline failure and mutant rejection validate tests, not model capability. Root `integration-manifest.json` and task-local selfcheck evidence record actual execution.

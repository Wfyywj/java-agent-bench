# Changelog

## Planner export placeholders — 2026-10-28

- The comparison planner no longer prefills an experiment name, control id, treatment id, model text, repeat count, budget, or seed. Those old strings are not model, control, or treatment values.
- Export is refused while any of those fields is empty or still one of the old placeholders. The page and the JSON both say the file is a planning draft, not executable, and an empty cost is unknown.
- A checked implementation tag shows its implementation id once.

## M1 discovery status — 2026-10-27

- `catalog/implementations.json` marks B02-slice, S01-slice, S04-slice, S04-spring, G01-slice, and G05-slice as `gates_green` when `engineering/m1-gates/evidence/summary.json` and the per-task four-gate files agree. `slice_kind` keeps `runnable_slice` or `runnable_integration_slice`. `security` stays `not_a_secure_sandbox`, `model_evaluated` stays false, and `full_catalog_ready` stays false.
- The original 25 designs stay `status: design_only`. B02, S01, S04, G01, and G05 add `slice_implementation` pointing at those slices. `design_only` is not “nothing executable”, and `gates_green` is not full catalog ready.
- `scripts/build_implementations.py` derives the status from the M1 evidence. The site reads that status for the five catalog cards and their slice panels.

## M1 four-gate check — 2026-10-27

- `python3 scripts/check_engineering.py --m1` runs B02, S01, S04, S04-spring, G01, and G05 reference / baseline / mutant / repeat gates and exits non-zero on failure.
- Per-task evidence is `evidence/m1-four-gates.json`. The aggregate is `engineering/m1-gates/evidence/summary.json`. These tasks use the unfixed baseline as the nop-or-baseline gate; there is no separate nop fixture.
- The default `check_engineering.py` entry remains the full fixture suite. `check_fast.py` does not run these Java gates. `full_catalog_ready` stays false.

## Website entry honesty — 2026-10-27

- Static header links the real GitHub repository as「GitHub 源码」before JavaScript runs.
- Quick start and task details lead with `git clone` and `prepare`. ZIP stays optional because `dist/packages/` is not committed and hosting can fail.
- Quick start and runnable/slice details state that the current runner is trusted-code only and not a secure sandbox. `model_evaluated: false` is not shown as a model score.

## 0.3 usability preview — 2026-10-27

- Added offline experiment workspace doctor/init/status with explicit provider/model/version, separate baseline/candidate and guided next steps; no model execution or credential access.
- Added website quick-start command planning, explicit executable-variant selection, atomic/deduplicated evidence imports, browser backup/export/deletion and same-version evidence comparison.
- Imported evidence remains unauthenticated and is not a model score; local storage is opt-in, and raw logs may contain private data.
- Added a single offline tooling check entry point and a Chinese end-to-end quick-start guide.
- Browser layout/interaction QA is not established by DOM-stub tests; managed preview infrastructure remained unavailable during this release.

## CLI adapter preparation — 2026-10-27

- Added offline Codex CLI / Claude Code command planning, existing-trace normalization and source manifest/diff collection.
- No agent launching, credential reads, permission bypass, billing-route switch or actual-model integration claim.
- Added dedicated adapter CI; core workflow skips adapter/analysis/docs-only changes while retaining full verification for core changes.

## 0.2 development — 2026-10-27

- Added 25 scope-limited engineering slices, five per design tier, separately identified as B01-slice .. K05-slice. Full original designs remain design_only.
- Added common prepare/evaluate launcher, per-task participant whitelists, candidate provenance hashes and trusted-code execution gate.
- Added actual H2 JDBC/SQL slices; higher distributed scenarios remain explicitly local/file/protocol surrogates.
- Added independent verification audits that detected and corrected gateway identity, reservation identity, claim metadata, booking note, persisted loan state, page-limit, CSV content/header, HMAC shared-oracle and cache-counter gaps.
- Added real-data frontend detail smoke tests, seed-zero persistence, object storage validation, imported result checks and distinct engineering-slice result import.
- Added pinned read-only CI workflow and source-reproducible regression commands. Runtime CI status is separate from the presence of this file.
- No evaluated-model results, calibrated rank, hidden holdout or hostile-code sandbox claims.

## 0.1 development — 2026-10-27

- Initial 25 detailed original scenario designs, R01–R03 mechanism tasks, functional verifier kernel, public research references and private static website.

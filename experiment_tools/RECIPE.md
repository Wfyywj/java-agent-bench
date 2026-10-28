# Stage B: bounded synthetic recipe bridge

**SYNTHETIC TEST FIXTURES NOT MODEL RESULTS.** This is executable data-contract
plumbing for B01, not a real agent runner or a benchmark result. Python standard library
only, no installation, network, credentials, subprocesses, Java evaluation or model calls.
It prepares actual B01 allowlisted baseline files, but the replay outcome assertions are
explicitly fabricated **fixture observations**, not observed task correctness.

## Reproduce from repository root

```sh
PARENT=$(mktemp -d)
python3 -m experiment_tools.recipe example > "$PARENT/recipe.json"
python3 -m experiment_tools.recipe freeze --recipe "$PARENT/recipe.json" \
  --run "$PARENT/run" --allow-synthetic
python3 -m experiment_tools.recipe replay --run "$PARENT/run" --allow-synthetic
python3 -m experiment_tools.recipe analyze --run "$PARENT/run" --allow-synthetic
# Last command exits 2: valid INCOMPLETE report, intentionally containing missing slots.
cat "$PARENT/run/analysis/report.json"
# Independently consume the exported strict inputs:
python3 analysis_tools/paired_analysis.py --plan "$PARENT/run/plan.json" \
  --records "$PARENT/run/analysis/records.json" --allow-synthetic
# Also exits 2 for this incomplete fixture. Errors exit 1; complete reports exit 0.
```

Before freeze, edit `repeats` to just `[{"repeat":1,"A":"failure","B":"success"}]`
for a complete two-slot replay. Every invocation of freeze/replay/analyze requires
`--allow-synthetic`. No actual mode or external evidence importer exists.

## Contract and immutable lifecycle

`recipe.py example` emits the exact editable `recipe-1.0` contract. Exact keys are
required. It holds explicit synthetic A/B metadata, comparison track, B01, positive
unique repeats, planned synthetic states, and fixed policy. Missing configuration is
an error, never synthesized as actual metadata. The analysis validator independently
checks permitted comparison factors and all metadata. Budgets are fixture declarations,
not enforced execution limits. No factual CLI/environment/model version is inferred.

Freeze creates a **new, outside-repository** directory and all independent baseline and
candidate copies. It writes `frozen.json`, `plan.json`, `workspace-seal.json`, and
`slots/repeat-N-A|B/`. The frozen file binds the recipe, registration time, exact task
manifest, task files, preparation/adapter/bridge/analysis Python code and absolute run
path. Existing targets cannot be overwritten/refrozen. Moving a run or changing bound
sources fails closed: use a new run rather than making old evidence look current.
Registration time is the actual local freeze time, not independently notarized.

Replay is one-shot: an existing `replay/` cannot be overwritten. A failed partial
replay remains on disk for diagnosis, is not automatically retried or erased, and
cannot be exported without its complete valid ledger. No slots are replaced with
successful retries. Each planned slot has one `trial-envelope-1.0` JSON envelope in
`replay/`, and one entry in `ledger.json`, including absent/cancelled fixtures.

| State | Strict record | Interpretation |
|---|---|---|
| success | success | Synthetic assertion only; no candidate evaluation |
| failure | failure | Synthetic assertion, retained in denominator |
| infrastructure_failure | infrastructure_failure | Synthetic assertion, separately counted |
| missing | absent | Planned observation not available; incomplete analysis |
| cancelled | absent | **Cancellation before any attempted agent trial**; explicit terminal ledger entry; incomplete analysis |

Attempted cancellation, timeout, actual launch, execution retries, authenticated billing,
and evaluator outcome ingestion are deliberately unsupported. They require a future
runner and frozen policy, not a reinterpretation of these fixture states. Cancelled
slots do not vanish: they stay in the ledger and the strict report's planned denominator
and missing-slots list. `display.json` preserves cancellation separately from missing.

## Evidence and hashes

Each attempted fixture has original, tool-created `*-trace.json` and
`*-evaluation.json` **synthetic assertion artifacts**. Their exact bytes, fixture
identity, kind, state and freeze binding are checked during export. These are not CLI
logs and not Java evaluation reports. Reference/selfcheck/external files cannot be
imported or upgraded to agent trials. Envelopes and records use `synthetic_replay`;
`actual_agent_trials` is rejected. The strict analyzer now additionally accepts that
run kind only with synthetic class **and** explicit opt-in; its actual-trial checks and
existing fixture compatibility are unchanged.

- `source_content_sha256`: canonical sorted candidate file manifest (path, bytes,
  SHA256), excluding only root `PREPARED.json`. Includes prompt/support files, not
  just Java. Identical submission content has identical hashes despite preparation time.
- `workspace_artifact_sha256`: complete per-slot workspace snapshot, including
  preparation metadata, baseline, command plans and guides.
- `run_artifact_sha256`: canonical envelope without this field; transitively binds
  evidence-byte hashes, source identity, slot, status and replay timestamp.
- `freeze_sha256`: canonical frozen object without this field. Canonical serialization
  is sorted compact UTF-8 JSON (`ensure_ascii=False`). These local checks detect accidental
  changes; they are **not signatures or proof against a writer who recomputes hashes**.

`replayed_at` is an actual replay bookkeeping timestamp, **not agent start time**;
strict synthetic records place it in `started_at` only for synthetic temporal validation.
All model cost and agent elapsed measurements stay `null` with an unknown reason.
Replay CPU time is not relabeled agent duration. No tokens, cost or actual model metadata
are invented. Absolute paths/seals make runs location-bound, not portable archives.
Directories are independent copies, **not a security sandbox**.

## Analysis and UI handoff

`analysis/records.json` and frozen `plan.json` pass the existing strict analyzer;
`analysis/report.json` is its unmodified output. Analysis output is also create-once.
`analysis/display.json` (`synthetic-replay-display-1.0`) combines the explicit synthetic
label, all typed slot envelopes and strict report for a future UI consumer. It declares
`website_import_supported: false`: it is **not** compatible with the current website
result importer, and no `dist/app.js` change or completed website integration is claimed.
Grok can build a reader for this interface without inferring missing/cancelled outcomes.

Actual agent integration remains deferred until launch provenance, trace/evaluator
binding, exact environment/CLI/model/prompt/skill versions, isolation, timing, budget,
cancellation and billing conventions are verifiable. Do not relabel this demo as a pilot.

```sh
python3 -m unittest experiment_tools.test_recipe -v
python3 -m unittest discover -s experiment_tools -p 'test_*.py' -v
python3 -m unittest discover -s analysis_tools -p 'test_*.py' -v
```

`recipe.schema.json` is Draft 2020-12, with `#/$defs/recipe` and
`#/$defs/envelope`; shared arm metadata refers to the existing analysis schema.
Runtime validation additionally checks cross-slot uniqueness, exact hashes, source
freshness, timestamps, state-specific artifacts and immutable lifecycle. The optional
JSON Schema regression test runs when `jsonschema` is already available, otherwise
skips without installing it; runtime execution has no dependency on that package.

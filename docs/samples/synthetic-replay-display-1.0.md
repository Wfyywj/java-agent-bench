# `synthetic-replay-display-1.0` field guide

Interface sample for review before any frontend PR. The sibling JSON is one unmodified `analysis/display.json` from the recipe CLI. This PR does not change the website, the result importer, graders, analysis rules, or the data protocol.

## Sample

| | |
|---|---|
| File | [`synthetic-replay-display-1.0.example.json`](synthetic-replay-display-1.0.example.json) |
| Generator | `python3 -m experiment_tools.recipe` on `main` `cb3c0a08e00f9b1bf29893599e6e554cec721f8d` |
| Commands | The example → freeze → replay → analyze sequence in [TRUSTWORTHY_EXPERIMENTS.md](../TRUSTWORTHY_EXPERIMENTS.md) and [RECIPE.md](../../experiment_tools/RECIPE.md), including `--allow-synthetic` |
| Analyze | Exit **2**. Stdout `status` is `incomplete`, `records` 4, `planned_slots` 6, `website_import_supported` false |
| Bytes | 12898, canonical compact JSON plus a trailing newline, SHA-256 `c74166d536318c64addefbf3aaa938d7372c90c1767c21c10a490c921b8a5f8d` |

No nested evidence was trimmed. Each attempted slot stores only an evidence `path` and `sha256`. The trace and evaluation JSON files are not embedded. Freeze time and `replayed_at` enter the hashes, so a later run will not byte-match this file. It is a review sample, not a golden hash test and not a portable copy of the run directory.

## Schema id

Read the outer string only:

- `schema_version`: **`synthetic-replay-display-1.0`**

Do not treat these nested version strings as the display schema or as the website importer schema:

- `slots[].schema_version` is `trial-envelope-1.0`
- `analysis.schema_version` is `1.0` (the strict paired-analysis report, embedded for display)

`data_class` on the document, every slot, and `analysis` is exactly `SYNTHETIC TEST FIXTURES NOT MODEL RESULTS`. Every slot has `run_kind`: `synthetic_replay`.

## Do not import

`website_import_supported` is **`false`**.

This document must not go through the existing result importer. Do not present it as model scores or a leaderboard. Routing `analysis` alone into that importer is the same mistake: the nested report is display context for this synthetic drill, not a website result row.

## Banner

Any view of these slots or of `analysis` shows a persistent banner. Required copy:

- `SYNTHETIC TEST FIXTURES NOT MODEL RESULTS` (the `data_class` string, unchanged)
- `合成演练`

The banner says this is a synthetic drill: tool-written fixture assertions, not a model pilot and not Java evaluation output. It stays visible next to the slot list and the summary. It is not a tooltip, not a dismissible chip, and not replaced by a scoreboard title.

## Fields UI authors bind

### Planned slots

`slots` contains every planned slot. This sample has **6** entries. Do not hide a slot because its state is failure, missing, or cancelled, and do not rebuild the list from `analysis` alone.

Pair and arm counts live on the report:

- `analysis.overall.planned_pairs`: 3
- `analysis.overall.arms.A.planned` and `.B.planned`: 3 each
- `analysis.status`: `incomplete` while any planned slot has no strict record

Slot identity is `slots[].slot_id` (`repeat-<n>-A|B`) plus `slots[].identity` (`implementation_id`, `manifest_sha256`, `repeat`, `arm`). `freeze_sha256` on the document matches `freeze_sha256` on every slot.

### Success and failure

The slot state is `slots[].state`. Observed fixture assertions in this sample:

| `slot_id` | `state` | Strict record |
|---|---|---|
| `repeat-1-A` | `failure` | yes |
| `repeat-1-B` | `success` | yes |
| `repeat-2-A` | `infrastructure_failure` | yes |
| `repeat-2-B` | `cancelled` | no |
| `repeat-3-A` | `missing` | no |
| `repeat-3-B` | `failure` | yes |

`infrastructure_failure` stays its own outcome. It counts as non-success and is not dropped and not merged into `failure`.

Arm totals in `analysis.overall.arms` count only slots that became strict records. Here arm A is `successes` 0, `failures` 1, `infrastructure_failures` 1; arm B is `successes` 1, `failures` 1, `infrastructure_failures` 0. `success_rate` is null on both arms. `success_delta_B_minus_A` is null. `success_rate_bounds` are bounds under the missing-trial policy, not a point score and not a leaderboard cell. `denominator_policy` says missing trials are not imputed and failed trials are not dropped.

### Missing, separate from pre-execution cancelled

These are different `slots[].state` values. Both keep their place in `slots`, and both have `evidence: null`.

| State | Meaning | This sample | Suggested label |
|---|---|---|---|
| `missing` | Planned observation is not available | `repeat-3-A` | 缺失 |
| `cancelled` | Cancellation **before any attempted agent trial**. The ledger entry is terminal. This is not an in-run timeout and not an attempted cancel | `repeat-2-B` | 执行前取消 |

`analysis.missing_slots` lists **both** `repeat-2-B` and `repeat-3-A`, and both arms show `missing: 1`. The strict analyzer only records that no trial row exists. It does not preserve the cancelled-versus-missing distinction. Label each row from `slots[].state`. Do not render `cancelled` as 缺失.

### Evidence identifiers and hashes

Show the identifiers. Do not invent file bodies.

| Field | Role |
|---|---|
| `freeze_sha256` | Frozen recipe binding for this run |
| `slots[].source_content_sha256` | Candidate file manifest, excluding preparation metadata |
| `slots[].workspace_artifact_sha256` | Per-slot workspace snapshot |
| `slots[].run_artifact_sha256` | Envelope digest |
| `slots[].evidence.trace.path` / `.sha256` | Synthetic trace assertion artifact |
| `slots[].evidence.evaluation.path` / `.sha256` | Synthetic evaluation assertion artifact |
| `analysis.plan_sha256` | Canonical plan digest inside the strict report |

Attempted slots (`success`, `failure`, `infrastructure_failure`) have both evidence objects. `missing` and `cancelled` have `evidence: null`. Hashes are local content checks, not signatures. The evidence files are fixture assertions (`execution: not_attempted` in the replay directory), not CLI logs and not Java grader reports.

### Cost and time: null is 「未知」

On every slot, `elapsed_seconds` is null and `cost_usd` is null. `resource_unknown_reason` is `No actual agent execution or resource measurement`.

Render those nulls as **「未知」**. Do not render `0`, `0s`, or `$0`.

The same rule applies to null report totals: `analysis.overall.arms.*.elapsed_seconds.total`, `cost_usd.total`, and `analysis.overall.paired_resources.*.mean_delta_B_minus_A`. `known_count` is 0. `known_sum` is 0 only because the sum of an empty set is 0; it is not a measured zero. Ignore `known_sum` when `known_count` is 0 and show 「未知」.

`replayed_at` is replay bookkeeping, not agent start time and not elapsed time. Arm `metadata.budget` (`wall_seconds`, `max_tokens`, `max_tool_calls`) is a declared fixture cap, not tokens spent or dollars charged. Model, tool, workflow, environment, and evaluator strings are `*@fixture-v1` labels, not probed CLI or model versions.

## What the UI must not do

- Mix these slots into actual results, a scoreboard, or a leaderboard.
- Relabel the page as a model pilot, an actual agent trial, or a Java evaluation.
- Send this file, or `analysis` extracted from it, through the existing result importer.
- Drop failed slots or fill in missing slots so `incomplete` looks `complete`.
- Collapse 执行前取消 into 缺失.
- Show null cost or time as zero.
- Treat `synthetic-model-*@fixture-v1` as a real model name on a comparison chart.
- Claim the website is wired up because this JSON exists. `website_import_supported` remains false until a separate acceptance says otherwise.

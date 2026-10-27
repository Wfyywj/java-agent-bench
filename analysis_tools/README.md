# Offline preregistered paired A/B analysis

This stdlib-only tool consumes a **plan registered before agent trials** and normalized
trial records. It does not run agents, models, patches, evaluators, or network calls.
It is not a leaderboard and makes no security or statistical-significance claims.

**Every bundled example is SYNTHETIC TEST FIXTURES NOT MODEL RESULTS.** Synthetic
records are rejected unless `--allow-synthetic` is explicitly supplied. That label is
carried into the report. No bundled result measures an actual model.

## Run

From the repository root (Python 3.9+):

```sh
python analysis_tools/paired_analysis.py \
  --plan analysis_tools/examples/synthetic-plan.json \
  --records analysis_tools/examples/synthetic-records.json \
  --allow-synthetic --bootstrap-samples 2000 --seed 1729
python -m unittest discover -s analysis_tools -p 'test_*.py' -v
```

For actual trials, omit `--allow-synthetic` and use inputs explicitly labeled
`actual_agent_trials`. Optional `--output PATH` writes JSON; otherwise stdout is JSON.
Exit codes: **0** complete valid report; **2** valid but incomplete report; **1** invalid
inputs (diagnostic on stderr, no report). Completeness is not evidence of good performance.
An existing `--output` file is overwritten on valid input; use a new output path per run.

`input.schema.json` is Draft 2020-12: `#/$defs/plan` describes plans and
`#/$defs/records` describes record arrays. Runtime validation is implemented in Python
without a JSON Schema dependency. Cross-record identity, metadata, timing, and track
constraints require the CLI in addition to any external schema validator.
Unknown keys and duplicate JSON object keys are rejected rather than ignored.

## Plan and comparison tracks

A plan specifies a stable `plan_id`, timezone-aware `preregistered_at`, data class,
track, exact A/B metadata, and a nonempty `pairs` array. Each pair explicitly names
`implementation_id`, the exact task `manifest_sha256`, and a positive `repeat` index.
**Each listed pair schedules exactly two slots: arm A and arm B.** List all planned
repeats before collecting results. Only one manifest version per implementation is
allowed within a plan. An identical duplicate pair is also an error.

The following metadata must be identical across arms except for permitted factors:

| Track | May differ between A and B | Must stay locked |
| --- | --- | --- |
| `model` | `model` | tools, workflow, budget, environment, evaluator |
| `workflow` | `tool`, `workflow` | model, budget, environment, evaluator |
| `budget` | `budget` | model, tools, workflow, environment, evaluator |
| `system` | model, tools, workflow, budget | environment, evaluator |

At least one permitted factor must differ. System comparisons compare configurations,
not model-only effects. Every trial's metadata must exactly equal its planned arm.
The report lists changed factors. There is no silent incomparable-results fallback.

Use immutable or fully resolved identifiers, not moving aliases: model snapshot plus
provider/decoding configuration, toolset version plus configuration digest, workflow
revision plus prompt digest, environment image/dependency digest, and evaluator
revision plus configuration digest. The identifiers are opaque strings to this tool;
it cannot resolve aliases or determine whether versions genuinely match. `budget`
contains positive `wall_seconds`, integer `max_tokens`, and integer `max_tool_calls`.
Unsupported limits or uncontrolled differences should be encoded in the appropriate
configuration identifier and documented; do not mislabel a system comparison as a
model comparison.

## Wrapping future actual agent results

1. Freeze task manifests, evaluator, environment, full arm configuration, repeats,
   assignment/randomization policy, outcome definitions, budget enforcement, timing,
   and billing conventions **before execution**. Archive the plan in an independently
   timestamped record. This tool only checks the declared registration/start times;
   it does not prove that registration happened or enforce run randomization.
2. Run actual agents externally using the chosen runner (Codex, Claude, API, etc.).
   Save original agent trace and original evaluator output. Do not run untrusted
   code through this analysis tool. Track all assigned slots, including setup failures.
3. Normalize one record per planned slot. Include unique `trial_id`, the exact plan,
   task manifest, repeat, arm, actual start time, and actual locked metadata.
   Set `run_kind` to `agent_trial` **only for a real assigned agent trial**. A runner
   setup failure may be an infrastructure-failure trial with trace evidence of the
   failed attempt; it must not be presented as a completed model response.
4. Hash original trace/evaluator evidence bytes with SHA256 and retain them separately.
   Evidence digests are required but the tool does not open or authenticate artifacts.
   If evaluator startup failed, retain its failure report as evaluation evidence.
5. Map evaluator outcomes under the preregistered policy: `success` only if all required
   checks pass; `failure` for agent/task failure (including budget exhaustion when so
   defined); `infrastructure_failure` for separately diagnosed runner/evaluator/service
   failures. Do not reclassify model failures to improve reported rates.
6. Record elapsed wall time and USD cost for **all** outcomes, not just successes.
   Use `null` with a nonempty corresponding `*_unknown_reason` when unavailable.
   Known measurements require a null reason. Zero means measured zero, not unknown.
   Establish one timing boundary and cost accounting policy across arms. Include failed
   requests/retries in the slot's elapsed/cost according to that frozen policy; never
   replace failed trials with successful retries or silently add extra slots. If policy
   requires a retry as a new repeat, it must already be in the plan.
7. Analyze records against the original plan; preserve incomplete reports. Never copy
   selfcheck/localreference outputs into agent records. This tool explicitly rejects
   those run kinds and **does not infer agent outcomes from reference outcomes**.

A harness-only result is insufficient: it lacks the agent trace and trial configuration.
The tool cannot independently establish genuine model use, correctness of normalization,
truth of costs, or authenticity of supplied hashes. Review original evidence separately.
The canonical sorted compact-JSON plan SHA256 in the report fingerprints the parsed
plan, not the original file bytes. No raw prompt, trace, credentials, or secret is needed
in this analysis input.

## Denominators and metrics

- Overall success is pair-weighted across **all preregistered task/repeat pairs**.
  Tasks with more repeats have greater weight. Per-task summaries show that explicitly.
- A complete arm's success rate is successes / planned slots. Both ordinary failures
  and infrastructure failures are non-success in this fixed denominator. Infrastructure
  counts are always separately reported; no success-only or infrastructure-filtered rate.
- Primary paired delta is **B minus A**, `(B_only - A_only) / planned_pairs`.
  Every planned pair contributes, including failures in both arms.
- Missing slots are listed with exact task/hash/repeat/arm; report status is incomplete.
  The primary delta is null, not a complete-case estimate. Incomplete arm rates are
  null with bounds [observed successes / planned, (successes + missing) / planned].
  Available pair outcome counts are descriptive and labeled with complete-pair counts.
- Elapsed/cost totals are null unless all planned values are known. `known_sum` is
  explicitly a partial sum, never an estimated total. Known, unknown, and missing
  coverage is shown; unknown reasons are counted. Failures are retained throughout.
- Paired resource mean deltas are null unless every planned pair has both measurements.
  A separately named **both-known subset** mean is descriptive only and can be biased;
  it is accompanied by both-known, unknown-value, and missing-record pair counts.

## Optional interval

`--bootstrap-samples N` (100–100000; default disabled) resamples entire implementation
clusters with replacement and keeps all repeats within each sampled task together.
Each draw computes the same pair-weighted success delta. The reported 95% percentile
interval uses floor/ceiling indices of sorted draws (no interpolation); default seed is
1729. Incomplete data withholds the interval. Fewer than 20 task clusters always emits
a sample-size warning; a one-task interval can be degenerate and is not evidence of
certainty. Bootstrap assumptions include approximately exchangeable task clusters;
shared dependencies and benchmark selection can invalidate extrapolation. The interval
is descriptive uncertainty under those assumptions, not a significance test, model
ranking, or guarantee of generalization.

## Scope

Files are independent of the existing benchmark harness and central result schema.
No runner adapter, model execution, provenance verifier, cost estimator, automatic
outcome inference, or publication is implemented. The fixture assertions test arithmetic
and validation behavior only. No package installation or network access is required.

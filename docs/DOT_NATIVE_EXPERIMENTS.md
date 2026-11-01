# dot-native exploratory experiments

This is a separate actual-agent, operator-orchestrated profile. It does not activate the strict Codex CLI preparation packet, bypass its launch gates, or generate synthetic data labeled as model output. `pilot.py` and its `launch_supported: false` remain unchanged.

## What can be claimed

- Fresh no-history dot participant conversations are given a frozen task and prompt; the workflow arm receives six pinned skill texts and must write a stage evidence artifact.
- Outputs, code differences, operator observations, source review and independent Java verifier reports are retained per slot.
- Agent completion and business verification are separate. Missing, cancelled, timed-out and failed attempts remain visible.
- Backend model identity/version, usage and cost remain null when unavailable. This is a comparison of this dot environment, not a named-model ranking.

## Boundaries

This environment shares a filesystem and tools. Prompts restrict access but do not enforce a security boundary or prove lack of contamination. Public task answers are not hidden. Exact model routing and provider raw trace are unavailable. Stage artifacts are participant claims until audited; receiving skill text is not proof of stage execution. Three repeats are exploratory and do not establish statistical significance.

Do not execute arbitrary output with `--trusted-code`. An operator must first inspect the exact candidate source and tests for network, process, host-file and other dangerous behavior, record the reviewed file hashes and reviewer decision, and only execute code they judge trustworthy. This is supervised local verification, not isolation. Rejected candidates remain unevaluated. The core evaluator security gate is unchanged.

## Commands

Run a separately recorded B02 preflight first and review it; do not count it in the comparison. Then freeze preparation after the harness is finalized:

```sh
python3 -m experiment_tools.dot_native prepare --root /absolute/new-experiment --skill-root /absolute/pinned-agent-skills
```

Run the 12 slots in plan order, each in a new no-history dot conversation. Before dispatch, call `begin --root ROOT --slot SLOT --agent-id RESERVED_AGENT_ID`; it verifies pristine inputs and writes an immutable operator start receipt. Use the same reserved agent ID when spawning. Record the exact receipt started_at and actual finished_at in observation.json. The parent applies a 900-second wall-time cap by best-effort cancellation; provider token/cost limits are not available. Supply its exact `PROMPT.txt` plus slot location. Keep tools and limits the same; no retries or evaluator feedback to participants. The operator records actual agent identifiers, status, observed elapsed time if available, final text and an explanation of the observed evidence. Never invent CLI exit codes or token/billing metadata. For workflow slots, audit `candidate/workflow-trace.md` against concrete artifacts separately.

Record source review with `approved_for_local_execution`, `reviewer`, `notes`, and exact `candidate_files` hashes. After trustworthy code is independently evaluated:

```sh
python3 -m experiment_tools.dot_native record --root /absolute/experiment --slot B02-r1-no-skill --observation observation.json --review review.json --report engineering.json
python3 -m experiment_tools.dot_native display --root /absolute/experiment > display.json
```

Omit review/report for unexecuted or rejected code; business status remains `not_evaluated`. Existing records cannot be overwritten. Record preparation source changes require a new frozen plan. Hashes detect consistency failures but are unsigned and do not authenticate execution or prevent coordinated tampering.

## Frontend contract for Grok

JSON schema: `experiment_tools/dot-native-results-1.0.schema.json`.

`dot-native-results-1.0`, data class `actual_dot_exploratory`, is separate from the synthetic display and `engineering-1.0` direct import. Do not silently import it as either. The display has 12 ordered `slots`, `smoke_included: false`, a `plan_sha256`, null backend identity, and visible `limitations`.

Each slot contains its ID, task, arm, repeat, input/prompt hashes, `execution_status` (`completed`, `failed`, `cancelled`, `timeout`, or `missing`), `business_status` (verifier status or `not_evaluated`), nullable elapsed seconds and cost, and nullable relative evidence path/hash. Preserve all slots and nulls. Treat relative evidence paths as text or validated bundle-relative links, never arbitrary fetch targets. Do not infer passing from completed. Smoke is shown separately, never in the 12-slot denominator. The detailed record contains candidate hashes, patch, observation, source review, independent report and unsigned-evidence caveat.

Raw traces and source evidence need operator review for privacy before public publication. Public reports must distinguish unavailable measurements, observed claims and checked evidence.

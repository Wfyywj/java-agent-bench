# D03: 多层缓存与消息积压的事故指挥
农资补贴申请在活动日出现重复受理与读状态回退，缓存命中率正常但消费积压增加。需在多因子证据中建立时间线，提出安全止血并实现根因修复。

Work from baseline/src and baseline/artifacts. Preserve CLI commands and durable state. Deliver corrected Java, regression tests, requirement-decisions.md, evidence-map.md and delivery-note.md. Read original-contract.json for the exact original acceptance contract. Do not modify verifier or assert full original acceptance: this is a runnable engineering slice, public development only. Reference and mutants are development controls, not hidden tests. No dependencies, network, model calls or installs.

Run `python3 run.py --candidate baseline/src`; compile Java 21 via the supplied module compiler runner. Commands mutate a locked atomic state file and append an audit journal. Evaluate crash/restart and rollback, not only final console output. Process crash consistency does not claim power-loss or distributed transaction durability.

## Implemented boundary
Deterministic explicitly labeled simulation of stale two-level cache rules, duplicate acceptance, out-of-order projection, backlog and lock-pressure recovery; raw offset clocks and structured diagnosis.

## Not claimed
Metrics are simulation counters, not measured hardware/database performance. Fixed causal fixture is not production diagnosis generalization.

Operator command: `python3 run_selfcheck.py --candidate /absolute/submission` (submission/src/Main.java). Only agent-files.json whitelisted assets are participant-facing. Public development controls are not hidden evaluation.

Diagnosis deliverable: artifacts/diagnosis.json must label simulation=true; include normalized_timeline (event and time), two hypotheses (freshness and lock-amplification) with evidence/experiment/conclusion, recovery (tenant, max_batch, dry_run, stop_if_locks_above), unsupported conclusions, communication and rollback. The provided clocks have known offsets; normalize before inferring order. Operator verification checks structured evidence anchors as well as executable fixes; free prose alone is insufficient.

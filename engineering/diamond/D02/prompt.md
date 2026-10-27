# D02: 事件驱动预约系统的模型化测试
多诊室预约的取消、改期和支付事件存在难复现竞态。为已有多服务实现建立独立模型与自动历史缩减，修复至少一个真实可复现缺陷。

Work from baseline/src and baseline/artifacts. Preserve CLI commands and durable state. Deliver corrected Java, regression tests, requirement-decisions.md, evidence-map.md and delivery-note.md. Read original-contract.json for the exact original acceptance contract. Do not modify verifier or assert full original acceptance: this is a runnable engineering slice, public development only. Reference and mutants are development controls, not hidden tests. No dependencies, network, model calls or installs.

Run `python3 run.py --candidate baseline/src`; compile Java 21 via the supplied module compiler runner. Commands mutate a locked atomic state file and append an audit journal. Evaluate crash/restart and rollback, not only final console output. Process crash consistency does not claim power-loss or distributed transaction durability.

## Implemented boundary
Event-driven booking, capacity and payment state in separate JVM command invocations; independent Python model, reproducible seeded legal histories, asynchronous projection tick and agent-generated history mutation matrix with legal deletion shrinker.

## Not claimed
Serialized deterministic scheduling only, no real message broker or simultaneous service processes; deletion-1-minimal is not globally minimum; no hidden seeds.

Operator command: `python3 run_selfcheck.py --candidate /absolute/submission` (submission/src/Main.java). Only agent-files.json whitelisted assets are participant-facing. Public development controls are not hidden evaluation.

Test-engineering deliverable: artifacts/suite.json is an array of legal operation histories, each an array of CLI argument arrays. Write tests rather than only changing the service. Operator evaluation executes this suite against the clean system and three known faulty implementations, reports a detection matrix and shrinks failing histories without dropping their creation/capacity prerequisites. A suite that never detects a fault does not pass the candidate interface.

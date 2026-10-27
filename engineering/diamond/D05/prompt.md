# D05: 可恢复批处理与外部额度服务
企业福利每月发券任务处理百万级成员，额度服务超时后重跑可能重复发券。实现分区检查点、幂等外部调用和取消恢复，保证部分失败可审计。

Work from baseline/src and baseline/artifacts. Preserve CLI commands and durable state. Deliver corrected Java, regression tests, requirement-decisions.md, evidence-map.md and delivery-note.md. Read original-contract.json for the exact original acceptance contract. Do not modify verifier or assert full original acceptance: this is a runnable engineering slice, public development only. Reference and mutants are development controls, not hidden tests. No dependencies, network, model calls or installs.

Run `python3 run.py --candidate baseline/src`; compile Java 21 via the supplied module compiler runner. Commands mutate a locked atomic state file and append an audit journal. Evaluate crash/restart and rollback, not only final console output. Process crash consistency does not claim power-loss or distributed transaction durability.

## Implemented boundary
Frozen membership snapshot, external provider ledger in durable file, unknown result after abrupt process halt, query-before-retry, checkpoint, fence, cancellation and poison isolation.

## Not claimed
Provider/controller use a local state file, not separate transactional systems. No wall-clock lease expiry, distributed quota service, cross-process multi-provider transaction, or real rate-limit timing model.

Operator command: `python3 run_selfcheck.py --candidate /absolute/submission` (submission/src/Main.java). Only agent-files.json whitelisted assets are participant-facing. Public development controls are not hidden evaluation.

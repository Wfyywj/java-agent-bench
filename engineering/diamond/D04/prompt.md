# D04: 插件隔离与供应链变更审查
物流报价服务允许租户安装受限规则插件，一次依赖升级改变了反序列化入口与类加载行为。审查依赖和实现变更，设计隔离及兼容替代方案。

Work from baseline/src and baseline/artifacts. Preserve CLI commands and durable state. Deliver corrected Java, regression tests, requirement-decisions.md, evidence-map.md and delivery-note.md. Read original-contract.json for the exact original acceptance contract. Do not modify verifier or assert full original acceptance: this is a runnable engineering slice, public development only. Reference and mutants are development controls, not hidden tests. No dependencies, network, model calls or installs.

Run `python3 run.py --candidate baseline/src`; compile Java 21 via the supplied module compiler runner. Commands mutate a locked atomic state file and append an audit journal. Evaluate crash/restart and rollback, not only final console output. Process crash consistency does not claim power-loss or distributed transaction durability.

## Implemented boundary
Manifest supply-chain review plus allowlisted expression DSL; explicit dependency and permission denial, harmless write marker probe, input and instruction budgets, clean tenant execution after rejection, redacted audits.

## Not claimed
Not a sandbox for arbitrary Java plugins. No classloader isolation claim. Java serialization and legacy Java plugins are rejected; OS network enforcement and real CPU preemption are not implemented. Trusted local fixture only.

Operator command: `python3 run_selfcheck.py --candidate /absolute/submission` (submission/src/Main.java). Only agent-files.json whitelisted assets are participant-facing. Public development controls are not hidden evaluation.

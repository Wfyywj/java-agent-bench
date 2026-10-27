# D01: 配送账务在线分片迁移
配送合作社账务按区域迁移到分片库，同时必须允许旧客户端查询和记账。设计回填、增量追赶、切读及回滚，不能停机全量搬迁。

Work from baseline/src and baseline/artifacts. Preserve CLI commands and durable state. Deliver corrected Java, regression tests, requirement-decisions.md, evidence-map.md and delivery-note.md. Read original-contract.json for the exact original acceptance contract. Do not modify verifier or assert full original acceptance: this is a runnable engineering slice, public development only. Reference and mutants are development controls, not hidden tests. No dependencies, network, model calls or installs.

Run `python3 run.py --candidate baseline/src`; compile Java 21 via the supplied module compiler runner. Commands mutate a locked atomic state file and append an audit journal. Evaluate crash/restart and rollback, not only final console output. Process crash consistency does not claim power-loss or distributed transaction durability.

## Implemented boundary
Durable per-region migration controller, stable entry identity, dual writes, bounded backfill, exact key/amount gate, fencing and rollback reverse-copy check.

## Not claimed
No real source DB, two shard databases, asynchronous CDC, concurrent thread scheduling, crash between two independent DB commits or scale test.

Operator command: `python3 run_selfcheck.py --candidate /absolute/submission` (submission/src/Main.java). Only agent-files.json whitelisted assets are participant-facing. Public development controls are not hidden evaluation.

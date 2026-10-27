# G01: 库存预占与订单创建的跨服务一致性

户外装备租赁把库存拆为独立服务，订单创建超时重试后出现幽灵预占。实现可恢复工作流，保障租期重叠约束并保留人工修复入口。

Repair baseline sources only; preserve public signatures. Inspect CONTRACT.md and diagnostic-evidence.md. Run `python run.py baseline` to reproduce, then `python run.py PATH_TO_CANDIDATE`. Submit a patch, evidence map, regression tests, decision record and rollback note. Do not edit fixtures/verifier. Public development tests do not establish unseen-task performance.

The packaged public smoke is `public-tests/Smoke.java`; compile it with your sources using Java 21 and run `publictests.Smoke`. The full public development verifier runs evaluator-side via `run_selfcheck.py --candidate ABS_PACKAGE`; this entrypoint is intentionally not part of agent input.

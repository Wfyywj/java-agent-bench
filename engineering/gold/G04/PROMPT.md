# G04: 权限缓存优化 PR 的对抗审查

组织协作平台提交权限缓存优化：延迟下降但撤权可能迟迟不生效。审查跨仓补丁，复现租户键碰撞、失效消息丢失与负缓存问题，并给出分级修复。

Repair baseline sources only; preserve public signatures. Inspect CONTRACT.md and diagnostic-evidence.md. Run `python run.py baseline` to reproduce, then `python run.py PATH_TO_CANDIDATE`. Submit a patch, evidence map, regression tests, decision record and rollback note. Do not edit fixtures/verifier. Public development tests do not establish unseen-task performance.

The packaged public smoke is `public-tests/Smoke.java`; compile it with your sources using Java 21 and run `publictests.Smoke`. The full public development verifier runs evaluator-side via `run_selfcheck.py --candidate ABS_PACKAGE`; this entrypoint is intentionally not part of agent input.

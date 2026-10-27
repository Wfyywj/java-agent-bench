# G03: 离线巡检上传协议的兼容迁移

巡检终端可离线七天，服务端升级附件协议后旧终端积压数据无法提交。修复 SDK、上传服务与工单服务，确保断点续传和历史协议兼容。

Repair baseline sources only; preserve public signatures. Inspect CONTRACT.md and diagnostic-evidence.md. Run `python run.py baseline` to reproduce, then `python run.py PATH_TO_CANDIDATE`. Submit a patch, evidence map, regression tests, decision record and rollback note. Do not edit fixtures/verifier. Public development tests do not establish unseen-task performance.

The packaged public smoke is `public-tests/Smoke.java`; compile it with your sources using Java 21 and run `publictests.Smoke`. The full public development verifier runs evaluator-side via `run_selfcheck.py --candidate ABS_PACKAGE`; this entrypoint is intentionally not part of agent input.

# G02: 计费规则版本化与历史重算

城市储物柜按存放区间计费，新规则上线后客服发现历史账单被当前规则重新解释。设计版本化规则与可审计重算，不能覆盖已确认账单。

Repair baseline sources only; preserve public signatures. Inspect CONTRACT.md and diagnostic-evidence.md. Run `python run.py baseline` to reproduce, then `python run.py PATH_TO_CANDIDATE`. Submit a patch, evidence map, regression tests, decision record and rollback note. Do not edit fixtures/verifier. Public development tests do not establish unseen-task performance.

The packaged public smoke is `public-tests/Smoke.java`; compile it with your sources using Java 21 and run `publictests.Smoke`. The full public development verifier runs evaluator-side via `run_selfcheck.py --candidate ABS_PACKAGE`; this entrypoint is intentionally not part of agent input.

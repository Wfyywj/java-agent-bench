# S01: 押金退款回调的乱序状态机

共享工具平台的退款回调可能重复或乱序：成功后收到处理中，用户页面会回退。修复接收端与账单投影，不能重放真实支付请求。

## Executable assignment
Signed refund callback CLI, atomic persisted event receipts and billing projection; fault injection before commit and after commit with restart replay.

Fix `baseline/src` while preserving CLI contracts. The evaluator launches a new JVM for each command and checks durable outcomes. Submit a directory with `src/` plus requirement-decisions.md, evidence-map.md, regression-tests/ and delivery-note.md. Documentation has supplied review anchors but is not automatically scored in this slice.

## Binding decisions
Keep success terminal versus processing/cancellation; terminal conflicts queue manual review. Cancellation is a request, not proof money cannot move: later success supersedes cancellation. Missing sequence rejects 422; unknown refund rejects 404; same sequence/different body is conflict.

## Boundaries
No HTTP adapter, real payment dispatch, database transaction engine, distributed delivery, fsync/power-loss guarantees, or production secrets.

Public development benchmark only. No hidden tests claimed. Do not edit the trusted evaluator or oracle. No network at evaluation time. Use only synthetic fixtures; no production calls or secrets.

## Run
From the benchmark checkout: `python3 engineering/silver/S01/run_selfcheck.py --candidate /absolute/path/to/submission`.
For H2 tasks, first explicitly run `python3 engineering/silver/setup_h2.py`; jar is digest-verified and never committed. Candidate evaluation accepts package with src/, or src itself. Only trusted local Java may run: this is not a hostile-code sandbox.

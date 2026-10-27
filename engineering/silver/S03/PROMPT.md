# S03: 多租户维修工单导出的权限闭环

物业后台新增异步工单导出，列表接口有权限但下载链接可跨租户读取。修复创建、任务执行与下载全链路授权。

## Executable assignment
File-backed async export command flow with create/worker/download authorization, revoked membership, explicit job scope on reused worker instance, expiry, safe synthetic CSV columns.

Fix `baseline/src` while preserving CLI contracts. The evaluator launches a new JVM for each command and checks durable outcomes. Submit a directory with `src/` plus requirement-decisions.md, evidence-map.md, regression-tests/ and delivery-note.md. Documentation has supplied review anchors but is not automatically scored in this slice.

## Binding decisions
Current membership required at creation, execution and download. Download restricted to task owner; expiry boundary now>=expiry. Unknown job 404, unauthorized 403, pending 409, expired 410. Prefix formula-leading text with apostrophe; exported columns only id/name.

## Boundaries
CLI rather than REST/object-store URLs; principal is trusted adapter input, not authentication. No real object-storage signing, HTTP non-enumeration policy, cross-process worker pool or external IAM.

Public development benchmark only. No hidden tests claimed. Do not edit the trusted evaluator or oracle. No network at evaluation time. Use only synthetic fixtures; no production calls or secrets.

## Run
From the benchmark checkout: `python3 engineering/silver/S03/run_selfcheck.py --candidate /absolute/path/to/submission`.
For H2 tasks, first explicitly run `python3 engineering/silver/setup_h2.py`; jar is digest-verified and never committed. Candidate evaluation accepts package with src/, or src itself. Only trusted local Java may run: this is not a hostile-code sandbox.

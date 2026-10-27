# S02: 优惠资格字段的跨仓兼容升级

合作社采购从单一会员等级改为资格列表，网关、订单服务和客户端 SDK 分处三仓。定位字段传播链并完成可滚动发布的升级。

## Executable assignment
Independently compiled SDK/gateway/service module snapshots with old/new request matrix, dual-write downgrade, list precedence and authoritative server entitlements.

Fix `baseline/src` while preserving CLI contracts. The evaluator launches a new JVM for each command and checks durable outcomes. Submit a directory with `src/` plus requirement-decisions.md, evidence-map.md, regression-tests/ and delivery-note.md. Documentation has supplied review anchors but is not automatically scored in this slice.

## Binding decisions
New explicit eligibilityCodes wins even when empty; omitted (~) falls back to legacy level. Lists accept MEMBER/STUDENT, select an owned STUDENT first then MEMBER. Unknown codes fail 422. New SDK dual-writes level; new-only calls downgrade to NONE on old service. Client claims never create server entitlement.

## Boundaries
No real separate Git histories, remote HTTP schemas, generated client runtime, deployed telemetry, or rolling production experiment.

Public development benchmark only. No hidden tests claimed. Do not edit the trusted evaluator or oracle. No network at evaluation time. Use only synthetic fixtures; no production calls or secrets.

## Run
From the benchmark checkout: `python3 engineering/silver/S02/run_selfcheck.py --candidate /absolute/path/to/submission`.
For H2 tasks, first explicitly run `python3 engineering/silver/setup_h2.py`; jar is digest-verified and never committed. Candidate evaluation accepts package with src/, or src itself. Only trusted local Java may run: this is not a hostile-code sandbox.

# S05: 订单搜索慢查询的证据化修复

二手书交易平台新增“最近有沟通”筛选后搜索变慢。分析执行计划、查询构造与数据分布，给出不改变权限和结果集的修复。

## Executable assignment
Actual H2 relational fixture, EXISTS semi-join, stable ordering, tenant predicate, counted SQL statements across page sizes, measured H2 EXPLAIN index evidence.

Fix `baseline/src` while preserving CLI contracts. The evaluator launches a new JVM for each command and checks durable outcomes. Submit a directory with `src/` plus requirement-decisions.md, evidence-map.md, regression-tests/ and delivery-note.md. Documentation has supplied review anchors but is not automatically scored in this slice.

## Binding decisions
Result requires a conversation at/after since and same tenant/order; EXISTS prevents duplicates with dense histories. Sort created DESC,id ASC, page limit 1..1000. Fixture includes empty conversations, tied creation timestamps and 80% dominant tenant.

## Boundaries
H2 is not PostgreSQL; PostgreSQL EXPLAIN ANALYZE, production cardinality estimates, index lock duration, latency/SLO and connection pooling remain unmeasured. Counter covers search SQL, excludes fixture loading and EXPLAIN.

Public development benchmark only. No hidden tests claimed. Do not edit the trusted evaluator or oracle. No network at evaluation time. Use only synthetic fixtures; no production calls or secrets.

## Run
From the benchmark checkout: `python3 engineering/silver/S05/run_selfcheck.py --candidate /absolute/path/to/submission`.
For H2 tasks, first explicitly run `python3 engineering/silver/setup_h2.py`; jar is digest-verified and never committed. Candidate evaluation accepts package with src/, or src itself. Only trusted local Java may run: this is not a hostile-code sandbox.

## Evaluated repository API and measurements
Preserve public `bench.SearchRepository.search(java.sql.Connection, String, long, int)` returning `List<bench.Order>` and `Order.id()`. The evaluator supplies its own H2 fixture and JDBC Connection through an evaluator-owned dynamic proxy. It counts actual statement `execute*` calls, independently of your diagnostic `queries` field. Existing CLI output is also tested. Fixture setup is excluded from measured repository queries. The inclusive `created >= since` boundary is exercised at an exact message timestamp (1800).

# S04: 配送批次取消的事务回归

社区团购取消配送批次后，部分库存被释放但订单仍待配送。找到代理事务失效与批量异常处理交互，修复而不锁住整张订单表。

## Executable assignment
Actual H2 JDBC transaction and JDK dynamic proxy entry; batch-row locking, stock/orders atomic rollback, checked/runtime injection, independent concurrent connections for cancellation versus shipping.

Fix `baseline/src` while preserving CLI contracts. The evaluator launches a new JVM for each command and checks durable outcomes. Submit a directory with `src/` plus requirement-decisions.md, evidence-map.md, regression-tests/ and delivery-note.md. Documentation has supplied review anchors but is not automatically scored in this slice.

## Binding decisions
Whole batch succeeds or fails. Ship/cancel lock the same batch row before checking/updating; shipped order blocks all cancellation. Repeated cancel returns duplicate with no inventory delta. Transaction entry owns connection and commit.

## Boundaries
H2 is not PostgreSQL. JDK Proxy is not Spring AOP: Spring self-invocation, propagation configuration and connection-pool exhaustion remain unmeasured. One fixture batch; no production lock/load calibration.

Public development benchmark only. No hidden tests claimed. Do not edit the trusted evaluator or oracle. No network at evaluation time. Use only synthetic fixtures; no production calls or secrets.

## Run
From the benchmark checkout: `python3 engineering/silver/S04/run_selfcheck.py --candidate /absolute/path/to/submission`.
For H2 tasks, first explicitly run `python3 engineering/silver/setup_h2.py`; jar is digest-verified and never committed. Candidate evaluation accepts package with src/, or src itself. Only trusted local Java may run: this is not a hostile-code sandbox.

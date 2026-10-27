# B03 — 冷链箱检索分页不丢单

你维护 `baseline/src/` 的 Java 21 单服务。仓库操作员报告：同秒入库的箱子跨页消失，扩大页大小暂时掩盖了问题。请定位并修复，而不是更换接口或返回全量列表。

## 输入证据
- `evidence/warehouse.csv`：合成仓库导出，44 条数据，north 36 条，同秒每组 12 条，文件顺序不等于 API 顺序。
- `evidence/incident.log`：录制的可重现故障摘要，不是生产记录。
- `evidence/api-contract.md`：现有接口约定。
- `src/BoxRepository.java` 为只读导出适配器；每次请求重新读取文件，明确不提供快照隔离。数据库部署/查询计划不属于本包已验证范围。

## 任务与提交
1. 修复稳定全序 `(receivedAt,id)` 与游标比较，包括 asc / desc。
2. 保留受控 400、游标租户/过滤条件绑定与空结果/末页契约。
3. 增加至少三页同秒数据、非法 token、跨租户、跨过滤条件及新增/删除回归测试。
4. 提交 `requirement-decisions.md`、`evidence-map.md`、`regression-tests/`、`delivery-note.md`。说明非快照语义、排除解释、真实执行情况、恢复步骤及风险。不得声称未运行的测试通过。

本包是公开开发夹具，不是隐藏测试或安全沙箱。只修改候选 src 和提交产物，不修改验收器。`reference/` 与 `verifier/` 是维护者的公开自检资产，正式评估应独立保留。此处不提供模型评分或经校准的难度结论。

执行 `python3 run_selfcheck.py --candidate baseline` 可运行候选。完整维护者回归为 `python3 run_selfcheck.py`。

The standardized candidate interface accepts a package root containing `src/`. The explicit legacy alternative is `--candidate-src /absolute/source-directory`.

## Prepared workspace layout
The sanitized presentation copy contains `src/` (from repository `baseline/src/`), the prompt, task metadata, and the explicitly listed public input files under `evidence/`. It does not include the local evaluator, reference answers, verdict/diagnosis contracts, or selfcheck results. Run evaluation commands from the benchmark repository, passing this package root with `--candidate`. The original repository remains public; this is presentation separation, not a hidden or secure evaluation.

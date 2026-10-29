# 定向反例：旧证据绿灯、缺失忽略、合成冒充

对照 [2026-10-28 能力实测](../../assessments/2026-10-28-capability-audit.md) 的 F3，以及 [可信实验阶段](../../TRUSTWORTHY_EXPERIMENTS.md) 的证据新鲜度、严格分析和合成数据隔离。这是可重跑的反例包，不是新题，也不是模型成绩。没有外部模型调用，没有凭据，没有费用。B2 真实 CLI 闭环没有在这里完成。issue #3 的浏览器验收不在本目录。

基线是含已合并 #19 的 `main`（`0ae58c92cc1be3597ba39fc9629106eb4b9c58ad`）。三条反例都在该代码上被挡住。Java / M1 四门没有重跑：绿灯新鲜度由目录构建时的源码指纹决定，最窄命令是一次性副本里的 `python3 scripts/build_implementations.py`。

| 类别 | 审计对应 | 本分支 | 从仓库根目录重跑 |
|---|---|---|---|
| 旧证据绿灯 | F3；阶段 A2 | **blocks** | `python3 docs/acceptance/fixtures/directed-counterexamples/stale-gates-green/repro.py` |
| 缺失忽略 | 严格分析不得丢掉预定槽位；recipe 示例退出 2 | **blocks** | `python3 docs/acceptance/fixtures/directed-counterexamples/missing-planned-slots/repro.py` |
| 合成冒充 | `website_import_supported` 为 false；recipe 拒绝 actual/reference/selfcheck 包装 | **blocks** | `python3 docs/acceptance/fixtures/directed-counterexamples/synthetic-impersonation/repro.py` |

回归挂在现有测试上：`tests/test_m1_evidence_integrity.py`、`analysis_tools/test_paired_analysis.py`、`experiment_tools/test_recipe.py`。防御退回时，对应 `repro.py` 退出 1 且输出 `verdict: still-fails`，`python3 scripts/check_fast.py` 失败。退出 0 且 `verdict: blocks` 表示反例被挡住。

## 旧证据绿灯

```text
build_exit: 0
build_stdout: 26 candidate-adapter slices discovered; 5 gates_green; original catalog statuses remain design_only.
B02-slice: status=runnable_slice gate_status=stale
B02_slice_implementation: absent
historical_evidence_pass: True
evidence_bytes_unchanged: True
gates_green_before: B02-slice,G01-slice,G05-slice,S01-slice,S04-slice,S04-spring
gates_green_after: G01-slice,G05-slice,S01-slice,S04-slice,S04-spring
verdict: blocks
```

构建仍退出 0。改过的 B02 不再是 `gates_green`，历史证据文件的 `pass: true` 和字节都还在，其余五条绿灯保留。

## 缺失忽略

```text
full_plan_exit: 2
full_plan: status=incomplete planned_pairs=2 missing=1 delta=None arm_A_failures=1
cherry_picked_exit: 0
cherry_picked: status=complete planned_pairs=1 missing=0
recipe_analyze_exit: 2
recipe_analyze: {"status": "incomplete", "records": 4, "planned_slots": 6}
verdict: blocks
```

完整计划退出 2。只有把缺失槽位从计划里删掉的那份对照才退出 0；分析器不会自己做成那个对照。Recipe 示例仍是 6 个预定槽位、4 条记录、退出 2。

## 合成冒充

```text
actual_recipe_exit: 1
actual_recipe_error: only explicitly synthetic recipe-1.0 is supported
actual_run_created: False
allow_synthetic_omitted_exit: 1
evidence_probe: selfcheck: not matching synthetic evidence; reference/selfcheck/actual imports rejected
evidence_probe: localreference: not matching synthetic evidence; reference/selfcheck/actual imports rejected
evidence_probe: reference: not matching synthetic evidence; reference/selfcheck/actual imports rejected
evidence_probe: actual_data_class: not matching synthetic evidence; reference/selfcheck/actual imports rejected
website_import_supported=false
synthetic_records_without_opt_in_exit: 1
synthetic_records_without_opt_in_error: Invalid analysis input: synthetic fixtures require --allow-synthetic
display_import_error: display.json：不是支持的单次验收结果：需要已知 R 系列任务与 schema_version 1.0。本批未导入任何记录，已有结果保持不变。
results_after_r01: 1
results_after_display: 1
verdict: blocks
```

`display.json` 没有进入结果列表。合成演练页拒绝工程结果、普通 `schema_version` 1.0、recipe，以及 `website_import_supported` 不是 false 的文件。`dist/app.js` 未改。

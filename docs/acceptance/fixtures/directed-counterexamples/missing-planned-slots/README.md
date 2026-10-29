# 缺失忽略（预定槽位不能被悄悄丢掉）

阶段标准：[TRUSTWORTHY_EXPERIMENTS.md](../../../TRUSTWORTHY_EXPERIMENTS.md) 的严格分析，以及 [阶段交付记录](../../../assessments/2026-10-28-stage-delivery.md) 里 recipe 示例必须 `incomplete`、退出 2。不完整计划必须显示为不完整，不能只留下成功记录看起来像一次完整对照。

输入都是合成夹具，不是 agent trial，也不是模型分数。

## 从干净克隆重跑

在仓库根目录：

```sh
python3 docs/acceptance/fixtures/directed-counterexamples/missing-planned-slots/repro.py
```

预期进程退出码 **0**，标准输出含 `verdict: blocks`。驱动执行下面两组命令。

完整计划（[`plan.json`](plan.json) 两个预定 pair，[`records.json`](records.json) 只有三条：repeat 2 的 B 缺失，repeat 2 的 A 是失败）：

```sh
python3 analysis_tools/paired_analysis.py \
  --plan docs/acceptance/fixtures/directed-counterexamples/missing-planned-slots/plan.json \
  --records docs/acceptance/fixtures/directed-counterexamples/missing-planned-slots/records.json \
  --allow-synthetic
```

预期退出码 **2**。报告 `status` 为 `incomplete`，`planned_pairs` 为 2，`missing_slots` 含 repeat 2 / arm B，`success_delta_B_minus_A` 为 null，arm A 的那条失败仍计入 `failures`。

被删掉槽位之后的对照（不要把它当成同一次计划的结果）：

```sh
python3 analysis_tools/paired_analysis.py \
  --plan docs/acceptance/fixtures/directed-counterexamples/missing-planned-slots/plan-cherry-picked.json \
  --records docs/acceptance/fixtures/directed-counterexamples/missing-planned-slots/records-cherry-picked.json \
  --allow-synthetic
```

这对文件退出 **0** 且 `complete`，因为计划本身不再包含缺失槽位。它用来说明“挑成功”长什么样。防御是：对完整 `plan.json`，分析器不会改成这个结果。

Recipe 示例（6 个预定槽位，其中缺失和执行前取消各一）：

```sh
PARENT=$(mktemp -d)
python3 -m experiment_tools.recipe example > "$PARENT/recipe.json"
python3 -m experiment_tools.recipe freeze --recipe "$PARENT/recipe.json" --run "$PARENT/run" --allow-synthetic
python3 -m experiment_tools.recipe replay --run "$PARENT/run" --allow-synthetic
python3 -m experiment_tools.recipe analyze --run "$PARENT/run" --allow-synthetic
```

最后一步预期退出码 **2**，`status` 为 `incomplete`，`records` 4，`planned_slots` 6，报告里 `missing_slots` 为 2，配对差分为 null。

若完整计划退出 0 或 `status` 变成 `complete`，驱动退出 **1** 并打印 `verdict: still-fails`。`analysis_tools/test_paired_analysis.py` 的 `test_directed_missing_planned_slot_repro_blocks` 会因此失败。

## 本分支输出摘录

```text
full_plan_exit: 2
full_plan: status=incomplete planned_pairs=2 missing=1 delta=None arm_A_failures=1
cherry_picked_exit: 0
cherry_picked: status=complete planned_pairs=1 missing=0
recipe_analyze_exit: 2
recipe_analyze: {"status": "incomplete", "records": 4, "planned_slots": 6}
verdict: blocks
```

结论：**blocks**。

# 合成冒充（夹具不能当成真实试验或普通网站导入）

阶段标准：[TRUSTWORTHY_EXPERIMENTS.md](../../../TRUSTWORTHY_EXPERIMENTS.md) 的数据隔离，以及 [阶段交付记录](../../../assessments/2026-10-28-stage-delivery.md)：`website_import_supported` 为 false；recipe 拒绝把 actual / reference / selfcheck 包装成合成回放，也拒绝反过来把合成回放包装成这些种类。

这是 B01 合成协议演练，不是 B2 真实 CLI 试验，不是 Java 验收，也不是模型分数。`dist/app.js` 没有改；检查使用已合并的 #19 只读合成演练页和原有结果导入。

## 从干净克隆重跑

在仓库根目录：

```sh
python3 docs/acceptance/fixtures/directed-counterexamples/synthetic-impersonation/repro.py
```

预期进程退出码 **0**，标准输出含 `verdict: blocks` 和 `website_import_supported=false`。

驱动使用这些输入：

| 文件 | 作用 |
|---|---|
| [`recipe-actual.json`](recipe-actual.json) | 示例 recipe，仅把 `data_class` 改成 `actual_agent_trials` |
| [`minimal-display.json`](minimal-display.json) | 模式探针：`website_import_supported` 为 false。不是一次试验 |
| [`display-website-true.json`](display-website-true.json) | 同一探针，但标志为 true |
| [`display-website-omitted.json`](display-website-omitted.json) | 同一探针，但缺少该标志 |
| [`ordinary-engineering.json`](ordinary-engineering.json) | 伪装成 `engineering-1.0` 的对象 |
| [`ordinary-result.json`](ordinary-result.json) | 伪装成 R 系列 `schema_version` 1.0 的对象 |
| [`synthetic-record.json`](synthetic-record.json) | 一条 `synthetic_replay` 记录 |
| [`check_website_import.mjs`](check_website_import.mjs) | 用 `dist/app.js` 的现有校验函数做导入拒绝检查 |

手工等价步骤：

```sh
PARENT=$(mktemp -d)
python3 -m experiment_tools.recipe freeze \
  --recipe docs/acceptance/fixtures/directed-counterexamples/synthetic-impersonation/recipe-actual.json \
  --run "$PARENT/run" --allow-synthetic
```

预期退出码 **1**，错误含 `only explicitly synthetic recipe-1.0 is supported`，运行目录不会被创建。

去掉 `--allow-synthetic` 的正常示例 `freeze` 也退出 **1**。

正常示例在 `--allow-synthetic` 下 freeze → replay 之后，驱动把 `repeat-1-A-trace.json` 的 `run_kind` 分别改成 `selfcheck`、`localreference`、`reference`，或把 `data_class` 改成 `actual_agent_trials`，并按新字节重算证据 sha256 和信封摘要（避免停在更早的哈希不符）。然后：

```sh
python3 -m experiment_tools.recipe analyze --run "$PARENT/run" --allow-synthetic
```

预期每次退出 **1**，错误为 `not matching synthetic evidence; reference/selfcheck/actual imports rejected`，且不会写出 `analysis/`。恢复原始证据后再 analyze，退出 **2**（示例本身不完整），`display.json` 的 `website_import_supported` 为 false，每条槽位的 `run_kind` 为 `synthetic_replay`。

把导出的记录改成 `selfcheck` / `localreference` / `reference`，或把计划和记录的 `data_class` 改成 `actual_agent_trials` 但留下 `synthetic_replay`，严格分析器拒绝。不带 `--allow-synthetic` 分析这些合成记录，退出 **1**。

网站侧：`check_website_import.mjs` 先导入真实的 `harness/results/R01-selfcheck.json` reference（结果列表变为 1），再导入生成的 `display.json`、最小 display、合成记录、工程对象、残缺 R 系列对象和 JSON 数组。这些都不得增加结果条数，错误含 `本批未导入任何记录`。合成演练校验拒绝 engineering-1.0、普通 schema 1.0、recipe-1.0、`website_import_supported: true`、缺少该标志，以及 JSON 数组；它接受标志为 false 的 display，并且不写入结果列表。

防御失败时驱动退出 **1**，输出 `verdict: still-fails`。`experiment_tools/test_recipe.py` 的 `test_directed_synthetic_impersonation_repro_blocks` 会因此失败。

严格分析器仍把元数据当作声明，而不是独立的来源证明。本反例不把“手工改写成 `actual_agent_trials` + `agent_trial` 的 JSON”说成已被密码学证伪；recipe 不会生成那种包装，现有结果导入也不会收下 display 或 `synthetic_replay` 记录。

## 本分支输出摘录

```text
actual_recipe_exit: 1
actual_recipe_error: only explicitly synthetic recipe-1.0 is supported
actual_run_created: False
allow_synthetic_omitted_exit: 1
allow_synthetic_omitted_error: explicit --allow-synthetic required; actual execution/import unsupported
evidence_probe: selfcheck: not matching synthetic evidence; reference/selfcheck/actual imports rejected
evidence_probe: localreference: not matching synthetic evidence; reference/selfcheck/actual imports rejected
evidence_probe: reference: not matching synthetic evidence; reference/selfcheck/actual imports rejected
evidence_probe: actual_data_class: not matching synthetic evidence; reference/selfcheck/actual imports rejected
analyze_exit: 2
website_import_supported=false
display_schema: synthetic-replay-display-1.0
record_run_kinds_rejected: True
relabel_actual_with_synthetic_replay_rejected: True
synthetic_records_without_opt_in_exit: 1
website_check_exit: 0
results_after_r01: 1
results_after_display: 1
display_import_error: display.json：不是支持的单次验收结果：需要已知 R 系列任务与 schema_version 1.0。本批未导入任何记录，已有结果保持不变。
verdict: blocks
```

结论：**blocks**。

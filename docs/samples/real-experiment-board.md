# 真实实验页

「真实实验」读取冻结的 dot-native 展示，不读取已经停用的 `provisional-real-experiment-board-0` 占位样例。

| | |
|---|---|
| 合同 | [DOT_NATIVE_EXPERIMENTS.md](../DOT_NATIVE_EXPERIMENTS.md) |
| Schema | [`experiment_tools/dot-native-results-1.0.schema.json`](../../experiment_tools/dot-native-results-1.0.schema.json) |
| 展示 | [`docs/experiments/2026-11-01-dot-native/display.json`](../experiments/2026-11-01-dot-native/display.json) |
| 说明 | [`docs/experiments/2026-11-01-dot-native/README.md`](../experiments/2026-11-01-dot-native/README.md) |
| 页面附注 | [`display-notes.json`](../experiments/2026-11-01-dot-native/display-notes.json)（不是结果协议，只给冒烟说明和 S01 裁定） |

`schema_version` 是 `dot-native-results-1.0`，`data_class` 是 `actual_dot_exploratory`。`smoke_included` 为 false。冒烟单独成区，不进入 12 格分母。对照区始终是 B02 / S01 × no-skill / workflow × 3。失败、取消、超时、缺失和未评估留在默认视图。`cost_usd` 为 null 时显示「未知」，不显示 `$0` 或数字 0。

版本与证据只展示 path 和 sha256，不抓取文件正文。S01 的独立裁定写在格子旁边，不改 `business_status`，也不声称 workflow 有效。这份展示不能导入「结果与证据」或「合成演练」。首页「已完成模型实测」保持 00。

本地预览：在仓库根目录执行 `python3 -m http.server 8765`，打开 <http://127.0.0.1:8765/dist/> ，点「真实实验」。不要部署公开站。

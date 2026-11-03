# 给 Grok：真实 pilot 结果 UI 后续任务（现在不导入伪结果）

## 背景

仓库 Wfyywj/java-agent-bench。已有前端 dist/、合成 B01 recipe 和 synthetic display 示例。
本阶段仅新增 `experiment_tools/pilot.py` / `PILOT.md` 离线准备：B02 单次 smoke，随后
B02/S01 × no-skill/workflow × 3 次共 12 槽位。所有槽位 NOT_RUN，没有真实模型成绩。
workflow 是用户 agent-skills 六核心阶段，local-delivery-only，不是新模型。
当前是 skill-context ablation；不能把文本提供显示成六阶段编排已完成。
原始真实 trace 默认仅本地保存，未经审阅、脱敏和授权不得上传或公开。

## 现在可交给 Grok：现有 engineering-1.0 的真实浏览器验收

公开站 v7 已匹配 benchmark 提交 `a2022a15e643f3ef4be7696adf2ccc433ae24ccf`。
已在可信参考解上得到 B02 10/10、S01 16/16；当前 app 的 Node DOM stub 接受两份结果。
**真实浏览器文件导入尚未验证**：云端浏览器文件选择器无法访问执行器文件，报文件不存在。
请在浏览器可访问的本机生成文件并验收；不需要新 schema，也不是模型试验。

前提：Python 3、Java 21+，已检出上述 benchmark 提交，以下命令在仓库根运行。
只执行仓库自带的可信 reference；不能将本命令用于不可信模型代码。

```sh
OUT=$(mktemp -d)
python3 scripts/engineering.py prepare B02 "$OUT/B02"
cp -R engineering/bronze/B02/reference/src/. "$OUT/B02/src/"
python3 scripts/engineering.py evaluate B02 "$OUT/B02" --trusted-code --output "$OUT/B02-reference.json"
python3 scripts/engineering.py prepare S01 "$OUT/S01"
cp -R engineering/silver/S01/reference/src/. "$OUT/S01/src/"
python3 scripts/engineering.py evaluate S01 "$OUT/S01" --trusted-code --output "$OUT/S01-reference.json"
printf 'Browser import files: %s\n' "$OUT"
```

在当前公开站 Results 页面导入两份现有 `engineering-1.0` 结果，逐项确认：

1. 两题显示参考解/可信自检结果，不得显示 actual model trial 或纳入模型成绩。
2. 重复导入不新增重复记录；导出、保存、刷新恢复与原结果一致。
3. 用副本篡改 manifest 摘要，确认拒绝错配文件，且先前有效记录仍保留。
4. 桌面和移动视口均可操作，错误提示、结果与版本可读。
5. 交回站点 URL/版本、执行命令、导入文件 SHA256、每项通过/失败/未测、截图和可复现步骤。

文件和记录仅本地；不上传原始 trace，不推送或部署代码。若文件选择器仍无法读取文件，
报告此项未验证，不用程序调用 importer 冒充真实浏览器文件选择验收。

## 可先做的任务

审阅现有 importer/展示边界，提出最小接入方案及需要后端提供的字段；不要将本准备包或
synthetic 示例改名为 actual。不要擅自编造 actual-result schema 或把 `not_run` 展示为失败/零分。
如实现占位展示，显著显示“未运行 / 启动条件待确认”，不得纳入成绩或榜单统计。
先回报计划，等真实证据协议冻结后再接正式 importer。

## 后续正式 UI 验收（等待真实协议与脱敏样本）

- 明确区分 preparation、synthetic、自检、actual；独立显示执行状态与业务验收状态。
- smoke 单独展示，不算入 12 次对比；展示全部槽位和失败/取消/缺失，不只展示成功。
- null 费用/时间显示“未知”，不转 0；模型、CLI、skill commit/config、任务/验收器版本可查。
- 无效版本、错配输入、重复身份、缺少真实证据、错误数据类别必须拒绝或清楚隔离。
- 新旧 importer 兼容回归、刷新状态、移动端、错误提示、取消/重复导入均要测试。
- 不推送/部署，除非用户另外授权；不要触碰正在独立部署的发布目录。

## 需要交回

最小实现计划、字段缺口、测试清单；正式实现时提供 diff、实测命令和未验证项。
当前缺口：隔离执行器、精确模型/auth/预算、真实进程及独立 verifier 证据和正式结果协议。

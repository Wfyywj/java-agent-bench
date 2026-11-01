# 真实实验页接入说明（占位）

当前网站「真实实验」是一块**只读占位板**。它用来把冒烟和对照分开摆好，并守住槽位、费用和证据的显示规则。正式字段和样例等固定格式到来后再换数据。这份说明和样例**不是**新的公开结果协议，也不是模型成绩。

## 现在读什么

| | |
|---|---|
| 页面 | `dist/index.html` 导航「真实实验」 |
| 适配 | `dist/app.js` 里的 `adaptExperimentBoard` |
| 样例 | [`real-experiment-board.placeholder.json`](real-experiment-board.placeholder.json) |
| 站点副本 | `dist/samples/real-experiment-board.placeholder.json`（与上面字节相同） |

样例的标记：

- `schema_version`: `provisional-real-experiment-board-0`
- `protocol_status`: `provisional_pending_fixed_format`
- `data_class`: `PLACEHOLDER SAMPLE NOT MODEL RESULTS`
- `website_import_supported`: `false`
- `counts_as_leaderboard`: `false`

`website_import_supported` 为 false。不要把这份 JSON 导入「结果与证据」，也不要送到「合成演练」。那两页会拒绝它。页面横幅不从文件里取，文件不能把自己标成排行榜后仍被打开。

槽位上的 `state` 是占位词，用来核对显示。`not_run` 表示还没运行、启动条件待确认，页面写成「未运行」，不写成失败，也不写成 0 分。执行状态和 `business_status` 分列；样例里失败格的业务状态是 null，页面显示「未知」，不从执行状态推断业务通过。

## 冒烟和对照

两个区由页面名册决定，不由某一格自报的 `phase` 决定。

- **冒烟**只有 `smoke-B02-no-skill`。它不计入 12，也没有重复编号。占位样例用 `repeat: null`。离线准备稿里曾把冒烟写成 repeat 0；这里不用 0，避免和费用 0 看混。
- **对照**固定 12 格：B02 / S01 × `no-skill`（对照臂）/ `workflow`（处理臂）× repeat 1、2、3。顺序与准备稿一致：repeat 1 和 3 先 no-skill，repeat 2 先 workflow。

`predetermined_slots` 必须与页面名册逐项一致（1 + 12）。`slots` 可以缺记录。缺的那一格仍留在对照区，状态按**缺失**显示。样例故意不写 `S01-r3-workflow`，用来核对这一点。

样例里 `B02-r1-workflow` 的 `phase` 误写成 `smoke`。该格仍留在对照区，并写明没有被挪进冒烟。

名册外的记录放在对照区下面，不隐藏，也不占 12 格。重复的 `slot_id` 同样留在名册外，不覆盖预定格。

## 默认视图留下的状态

对照区没有「只看成功」的筛选。样例里能看到：

| 预定格 | `state` |
|---|---|
| `B02-r1-no-skill` | `failure` |
| `B02-r1-workflow` | `cancelled` |
| `B02-r2-workflow` | `missing` |
| `B02-r2-no-skill` | `infrastructure_failure` |
| `B02-r3-no-skill` | `not_run` |
| `B02-r3-workflow` | `not_run` |
| `S01-r1-no-skill` | `failure` |
| `S01-r1-workflow` | `cancelled` |
| `S01-r2-workflow` | `not_run`（没有 `cost_usd` / `elapsed_seconds` 字段） |
| `S01-r2-no-skill` | `not_run` |
| `S01-r3-no-skill` | `failure` |
| `S01-r3-workflow` | 文件中没有这一条，页面仍显示为缺失 |

冒烟格是 `not_run`。取消和缺失用不同标签，不互相改写。

## 费用

沿用现有显示规则：未知是 null，不是测到的 0。

`cost_usd` 或 `elapsed_seconds` 为 null、缺字段、不是有限非负数，或同时有非空 `resource_unknown_reason` 时，页面显示 **「未知」**。不显示 `$0`，也不把未知写成数字 0。带了 unknown reason 的数字 0 仍按未知显示，因为原因表示这不是一次测量。只有没有 reason 的有限非负数才按测得数值显示，样例里没有这种数。

本页不读 `analysis`、`success_rate`、`score`、`leaderboard`、`cost_total`。文件里若出现这些键，只提示已忽略，不把数值画出来。

## 版本与证据

「打开版本指纹」和每一格的「版本与证据」打开同一只详情框。页面只展示字段，不拉取证据文件。

整板 `version` 目前读取：

- `fingerprint_status`（样例为 `unfrozen`，显示「未冻结」）
- `model`、`cli_tool`、`cli_version`、`auth_mode`
- `skill_repository`、`skill_revision`、`skill_config_sha256`
- `evaluator`
- `tasks.B02` / `tasks.S01` 的 `implementation_id`、`manifest_sha256`、`task_version`

null、缺字段、或数字（含 0）显示「未知」。样例里的 `implementation_id` 只是目录里的切片名字，不是这次运行已经绑定的证明。`manifest_sha256` 留空。

每一格另外读取可选的 `version`：`manifest_sha256`、`source_content_sha256`、`workspace_artifact_sha256`、`run_artifact_sha256`、`freeze_sha256`。证据沿用合成演练页已经在用的形状：`evidence` 为 null，或 `{trace:{path,sha256}, evaluation:{path,sha256}}`。样例里的 path 以 `placeholder/not-a-published-...` 开头，仓库里没有这些文件。sha256 为 null 时显示「未知」，不补 `000…`。

## 换上正式样例时改哪里

只改 `adaptExperimentBoard` / `validateExperimentBoard` 和这份样例。视图继续要求：冒烟与对照分区、12 个对照格始终可见、失败 / 取消 / 缺失不从默认视图消失、未知费用不是 0、版本和证据可打开。在固定格式落地之前，不要把 `schema_version` 改成看起来已经冻结的协议名，也不要把 `data_class` 改成 actual。

## 本地预览

在仓库根目录：

```sh
python3 -m http.server 8765
```

浏览器打开 <http://127.0.0.1:8765/dist/> ，点「真实实验」。不要部署公开站。静态页不会跑模型，也不会把样例写入浏览器里的结果列表。

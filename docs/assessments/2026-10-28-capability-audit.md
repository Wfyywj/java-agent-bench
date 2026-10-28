# Java Agent Bench：能力实测与下一阶段方向

日期：2026-10-28。固定审计提交：`5f4b58b54925b855cbe9ff6ffa0d30a1dc13c4c0`。

## 结论先行

**下一阶段应从“更多题目、更多绿灯”转向“验收可信 + 第一轮真实实验可复现”。**

现有项目已经有价值：分级场景设计、可执行工程切片、独立候选目录、基线/参考解/错误变体检查、网站及离线分析工具均已存在。但是它目前更接近“任务开发与功能验收工具箱”，还不是可以直接评出某个模型或 Skill 更好的完整实验平台。

本次实测没有调用 Codex CLI、Claude Code 或其他外部模型，没有读取认证信息或产生模型费用。参考解替换、错误补丁和 JSONL 都是明确标记的**可信合成测试输入**，不是 agent trial，更不是模型排名。测试在独立临时副本中完成，没有修改主仓库的实现、题目或历史证据。

## 一、实际测了什么

| 检查 | 实际结果 | 证明边界 |
|---|---|---|
| B01：Codex/Claude 两种离线准备计划 | doctor → init → 合成轨迹 normalize → collect → reference evaluate 跑通 | 没有启动两个真实 CLI；只是准备和证据组件联通 |
| B01 原始缺陷与参考解对照 | 原始缺陷 17 项检查中 9 项失败，decisions 未通过；完整参考替换 17 项全通过 | 证明本题现有验收能抓住已知原始缺陷，不证明覆盖全部错误 |
| B02/S01 门禁及现有错误变体 | 重新执行当前可信自检，基线失败、参考通过、已有错误变体被检出 | 现有门禁本身可以复演；不能据此保证不会误放新的错误修复 |
| B02/S01 新增近似错误修复 | 两份违反明确契约的修复分别连续两次通过现有验收 | 已发现实际漏检，详见下文；不是随机样本，不可估算全库漏检率 |
| 修改参考代码后重建目录 | 已知错误 reference 实际验收失败，但目录仍显示 gates_green | 历史证据与当前源码缺少充分绑定，存在陈旧绿灯 |
| Spring mutant 超时证据注入 | 所有 10 个 mutant 结果改为退出 124、无检查，四门仍为真 | 受控归一化/校验层测试，不是实际运行 10 个超时 Java mutant |
| 缺少 Java 的运行失败 | 子进程 PATH 为空时 --m1 退出 1，旧的 7 份绿证据原样保留 | 没有报告“命令成功”；风险是消费者继续使用旧文件，而未区分本次失败 |
| 外层超时与子进程清理 | 外层 1 秒超时返回后，独立 session 的测试子进程仍运行 | 使用真实调度函数和无副作用短命 sleep 替身；测试进程已显式清理 |
| 网站计划 → 严格 A/B 分析 | 网站草案、workspace manifest、trace/evaluation 原样传入均被拒绝 | 拒绝无效输入是正确行为；缺的是明确的协议转换与完整 trial 证据采集 |

## 二、两个具体的“错误修复拿到全绿”

### F1：B02 漏掉器材与借单的绑定校验

规范依据：`engineering/bronze/B02/prompt.md` 的冻结业务契约要求：器材不属于该借单时返回 `409 NOT_RETURNABLE`。

对参考解 `reference/src/ReturnService.java` 只做以下删除：

```diff
- !l.equipment().equals(r.equipment()) ||
```

保持其余逻辑不变。独立最小输入：`loan1` 原本绑定 `bat1`，首次归还请求却提交 `ball2`。

- 参考解实际返回：`Reply[status=409, body=NOT_RETURNABLE]`。
- 修改后实际返回：`Reply[status=200, body=loan=loan1;state=CLEANING]`。
- 现有 candidate evaluator 对错误版本连续两次判为通过，8/8 检查全绿。

**修复验收要求：**新增首次归还的错误器材断言，核对 HTTP/业务返回和持久状态；将该删除补丁纳入长期 mutant。补测试之后，参考仍通过、该 mutant 必须以明确业务断言失败被检出。

### F2：S01 只处理一个方向的终态冲突

规范依据：S01-A02 与 `requirement-decisions.md` 要求终态冲突转人工复核；不是只规定“成功后收到失败”一个方向。

对 `reference/src/bench/RefundService.java` 只删除：

```diff
- ||(old.equals("FAILED")&&next.equals("SUCCEEDED"))
```

发送签名合法的两条回调：`FAILED(seq=1)` → `SUCCEEDED(seq=2)`。

- 参考解：第二条返回 `409 manual_review`，最终状态 `FAILED|0|true`。
- 修改后：第二条返回 `200 stale`，最终状态 `FAILED|0|false`，未进入人工复核。
- 现有 candidate evaluator 对错误版本连续两次判为通过，10/10 检查全绿。

**修复验收要求：**对终态迁移做方向成对测试；至少覆盖成功→失败、失败→成功、同终态重放、较旧序号及持久化后重启。这个删除补丁必须作为新的错误变体保留。

这两项的意义不是“整个项目不可用”，而是说明：**参考解通过 + 当前 mutants 全死，仍然可能漏掉题面中的关键要求。** 每个 critical acceptance 应映射到至少一个正例、一个反例和可说明区别的断言，而不只看测试总数。

## 三、门禁证据与运行器的问题

### F3：历史 gates_green 可能被错误地用于新源码

在独立副本中修改 B02 reference，并进一步禁用现有验收能够抓住的 payload-conflict 逻辑：

1. 修改后的 reference 真实运行 candidate evaluator，`B02-A02_payload_conflicts` 失败。
2. 保留此前四门证据，运行 `python3 scripts/build_implementations.py`。
3. 构建仍退出 0，仍输出 6 个 gates_green，B02 仍为 gates_green。

现有 manifest hash、检查结果 digest 并不能替代“本次证据对应哪份候选/参考/验收器源码”的绑定。此项是**证据新鲜度与可复现性问题**，不是声称项目本来承诺了防恶意篡改。

建议固定 `evidence_fingerprint`，覆盖：任务 manifest、白名单、题面、baseline、reference、verifier、mutants、相关 harness/依赖配置。报告同时记录 run_id、开始/结束时间、退出类型、环境版本。目录生成时验证 fingerprint：变化或本次失败就显示 `stale` / `verification_failed`，不可继续无条件复用绿色状态。

### F4：不能把“超时”自动算作“错误变体被业务断言杀死”

基于 checked-in Spring capture，保留控制组，单独将 10 个 mutant 的测试状态替换为 exit=124、无断言结果。目前仍得到 reference/nop_or_baseline/mutants/repeat 全真，证据校验错误列表为空。

建议只把明确的业务/契约断言失败计为 semantic kill；编译失败、启动错误、基础设施超时、结果缺失分别记录。若某题确实把超时作为业务性质，必须提前定义对应断言、运行上限和独立证据，不可由通用退出码猜测。

### F5：失败运行必须与旧成功报告区分

仅在临时子进程设置空 PATH，实际执行 --m1 后因找不到 java 退出 1；六份题目证据及 summary 共七份文件保持旧内容，其中 summary.pass 仍为 true。

命令已经失败，并非进程退出码造假。问题在于后续只读证据文件的消费者可能不知道刚才失败了。

建议每次写独立 run 目录，失败也产生明确结果；latest 指针与目录构建选择规则要定义清楚。不能简单删除历史成功证据，也不能让“历史成功”冒充“当前版本、本次运行成功”。

### F6：超时返回不等于整棵进程树已退出

使用现有 default_executor 与 G05 运行函数，将 Java 替换为自建短命 sleep：外层 1 秒超时返回124时，独立 session 的子进程仍在运行。测试结束已清理它，没有修改宿主配置或终止无关进程。

建议用统一 supervisor 跟踪受控进程，或在适合的可丢弃环境中由 cgroup/容器/VM 生命周期兜底。至少新增“父超时后所有本次拥有的后代均停止”的回归。不要把仅 killpg 的工具标为完整恶意代码隔离。

F4–F6 与既有 [PR #12 的三条审查发现](https://github.com/Wfyywj/java-agent-bench/pull/12)一致，本次增加了受控复现，不是仅重复机器人结论。

## 四、当前产品闭环断在哪里

现有三种“计划”不是同一个东西：

1. 网站 `planning_draft`：用户规划草案，明确 `execution_supported=false`。
2. `experiment_tools` manifest：一个离线工作目录的身份和文件记录。
3. `analysis_tools` plan/records：冻结 A/B 条件、预定槽位、真实 trial 配置和证据哈希的严格分析输入。

实测中，把前两种文件直接作为第三种 plan 会退出1；把原始 normalized trace 或 evaluation 当 record 也被拒绝。**这不是应当放宽校验的 bug。** 真正缺的是中间的 Experiment Recipe / Trial Envelope：

- 草案在未填配置时只能保存为草案；冻结后生成明确的实验计划与每个 task/repeat/arm 槽位。
- 绑定 task、evaluator、环境、模型、CLI、prompt、skill/workflow、预算及计费口径。
- 记录真实启动、退出、超时、重试和取消；CLI 输出结束不能自动等于业务通过。
- 将原始 trace、候选提交和独立验收结果关联到同一个 trial。
- 自动产生严格分析输入，保留所有失败/缺失记录；未知费用仍为 null。
- 对 reference/selfcheck/synthetic 做强制区分，不能转换成真实 agent_trial。

先用合成回放把这些数据契约接通，不需要模型费用；随后再接入真正的隔离执行环境和两个 CLI。

另一个需区分的细节：两份相同参考源码仅因 `PREPARED.json.prepared_at` 不同，就产生不同整体提交哈希；collect 与 evaluator 的顶层 digest 格式也不同，虽然逐文件哈希一致。这不等于错误，但桥接时应分开 `source_content_hash` 和 `run_artifact_hash`，不能把准备时间差误认为代码差异。

## 五、建议的下一阶段顺序与完成标准

### 阶段 A：先修正“判卷器和绿灯”（最高优先）

范围限定为 F1–F6，暂停扩充题量。

完成标准：
- 两个新错误修复不能通过，reference 仍全部通过；反例有业务规范依据。
- timeout/missing report/基础设施失败不能混入 semantic kill。
- 修改绑定范围内源码后旧证据被标 stale；失败运行不会被旧 summary 遮住。
- 超时和取消后本次进程清理可验证。
- 新生成四门证据关联同一源码版本，并验证任务重复运行稳定性。

### 阶段 B：做一个能复演的实验闭环，而非更多手工 JSON

选择少量已修复任务，实现 Recipe → 独立工作区 → trial evidence → 严格分析 → 网站展示。先用合成回放检验契约，所有页面明确标为 synthetic。

完成标准：从一个冻结配置文件能准备 A/B 槽位；缺失、失败、取消、未知费用、版本不一致都能正确展示。不要为了“跑通”伪填模型、token、成本或把参考解冒充真实试验。

### 阶段 C：隔离运行后，再做小规模真实 pilot

建议先考虑 B02、S04-spring、G01 三种不同故障机制；两组配置、每题三次，共18个真实 trial。这只是检查天花板/地板/抖动和流程可行性的 pilot，不足以发布普适模型排行。

如果比较 Skill，固定模型、CLI、环境、预算与提示，仅改变 Skill；如果同时更换 Codex CLI/Claude Code 和模型，应称**完整系统比较**，不能归因于单个模型。

开始真实调用前仍需确定具体 CLI/模型版本、认证方式、允许权限和总预算。当前环境未发现 Docker/Podman 命令，也没有验证可用的隔离 runner；本次不安装、不创建访问凭据、不调用模型。

### 暂缓项

- 暂缓把25个设计全部升级为完整生产工程。
- 暂缓再做排行榜、总分或难度实测校准。
- 暂缓自研整套通用 agent 执行平台。
- UI 文案和移动端继续做，但不能替代验收可信度修复。

## 六、与 Grok Bot 的建议分工

这是建议，尚未替任何协作者认领任务，也未直接向外部 Bot 发指令。

- **本侧：**阶段 A 的业务反例、门禁证据绑定和运行器回归；随后定义 Recipe/Trial Envelope 与分析桥接。主要涉及 scripts、engineering verifier、schemas/tests。
- **Grok Bot：**[issue #8](https://github.com/Wfyywj/java-agent-bench/issues/8) 详情中文可读性与[issue #3](https://github.com/Wfyywj/java-agent-bench/issues/3) 真实浏览器验收：移动端、真实 JSON 导入/坏文件/重复文件、导出内容、存储恢复、弹窗与导航。
- **共同接口：**先冻结一个最小结果 fixture 和状态词典，再分头实现；同一轮 `dist/app.js` 由一方负责，另一方只 Review，避免互相覆盖。
- #5 的三波 M1 工作和 #7 的占位校验已经合并，不重做。当前只读核查未见 open PR，但不代表不存在尚未推送的工作。

`docs/ROADMAP.md` 仍有“私有部署/需登录”的旧描述，应同步成当前公开站和实际剩余验收项目；完整浏览器验收仍不能仅凭局部烟测勾选完成。

## 七、可借鉴而不是照搬的开源经验

Harbor 官方文档已有 job/trial、Codex/Claude Code agent 选择、超时/重试配置，以及 oracle/nop 验证路径。建议先做 **1 个现有 Java 任务的版本固定兼容性试验**，看能否复用执行与日志基础设施；不应把“接入框架”直接当作我们已经获得安全隔离或可信评分的证明。

来源（查阅于2026-10-28）：
- [Harbor run 文档](https://github.com/harbor-framework/docs/blob/main/cli/run.mdx)
- [Harbor task 创建与验证规范](https://github.com/harbor-framework/harbor/blob/main/skills/create-task/SKILL.md)
- [Harbor job 配置及锁定输入](https://github.com/harbor-framework/harbor/blob/main/src/harbor/models/job/config.py)

## 最终判断

现阶段最值得投入的，不是再加一批看起来复杂的题，而是让系统能可靠地回答：

> 这份错误修复为什么不能通过？这次绿灯对应哪份代码？这次 A/B 差异究竟来自什么？

先把这三件事做成可复演的证据，再跑真实 Skill/工作流 pilot，项目才会从“能展示任务”转向“能辅助工程决策”。

## 固定源码定位

- [B02 冻结契约](https://github.com/Wfyywj/java-agent-bench/blob/5f4b58b54925b855cbe9ff6ffa0d30a1dc13c4c0/engineering/bronze/B02/prompt.md)
- [S01 任务规范](https://github.com/Wfyywj/java-agent-bench/blob/5f4b58b54925b855cbe9ff6ffa0d30a1dc13c4c0/engineering/silver/S01/task.json)
- [M1 门禁实现](https://github.com/Wfyywj/java-agent-bench/blob/5f4b58b54925b855cbe9ff6ffa0d30a1dc13c4c0/scripts/m1_gates.py)
- [目录状态生成](https://github.com/Wfyywj/java-agent-bench/blob/5f4b58b54925b855cbe9ff6ffa0d30a1dc13c4c0/scripts/build_implementations.py)
- [严格分析输入说明](https://github.com/Wfyywj/java-agent-bench/blob/5f4b58b54925b855cbe9ff6ffa0d30a1dc13c4c0/analysis_tools/README.md)

# B02/S01：真实 workflow 实验的离线准备（不是 B2 执行器）

这是启动前的可审阅材料，不调用 Codex、不检查认证、不执行候选代码、没有真实模型结果。
现有 B01 synthetic recipe 完全不变；本入口不接受 synthetic 或 actual 结果导入。

## 固定设计

- 先一个 **B02 + Codex + no-skill smoke**，不计入正式对比。smoke 审阅后才决定启动下一阶段。
- 正式预留 B02/S01 × no-skill/workflow × 3 repeats，共 12 槽位，不挑选成功样本。
- 未来执行须固定同一模型、CLI、环境、任务输入、公共提示词、预算；只改变六阶段 workflow 的提供和调用。
- 当前处理语义是 **skill-context ablation（技能上下文对比）**。只有真实 trace 证明六阶段执行后，
  才能另外报告阶段遵循情况；提供文本不等于完成编排。
- 顺序固定：B02 后 S01；重复 1/3 无 skill 先、重复 2 workflow 先。小样本不是显著性或模型排名证据。
- workflow 使用 Wfyywj/agent-skills 的 `80e15acdf61d2cecf1ff79e9088a8149e64ffc1a`：
  clarify-task → plain-plan → implement-slice → verify-change → review-change → deliver-change。
  只读六个 SKILL.md；逐文件 SHA256 必须匹配代码中的冻结值。不安装或执行 skill 脚本。
- deliver-change 限制为本地交付；排除 learn-from-task/experiences 和跨试验记忆。
- smoke 条件与顺序是本准备方案的明确选择，冻结执行计划前可审阅修改，不能执行后改写。

## 离线使用

先自行获取上述固定提交的 skill 源码，工具不会联网或运行 Git：

```sh
python3 -m experiment_tools.pilot prepare \
  --skill-root /absolute/path/to/agent-skills \
  --destination /absolute/existing/parent/new-pilot-packet
python3 -m experiment_tools.pilot verify \
  --destination /absolute/existing/parent/new-pilot-packet
python3 -m unittest discover -s experiment_tools -p 'test_*.py' -v
```

目标必须在 benchmark 仓库外、与 skill 源码不嵌套且尚不存在。`inputs/` 是每题一次 allowlist
准备出的输入；所有槽位的 candidate 包括 PREPARED.json 均逐字节一致、独立复制，无共享硬链接。
`workflow/` 只出现在处理臂；no-skill 没有 workflow 的指导语或文件。
`manifest.json` 绑定输入、源码/验收器/准备器与技能摘要；`seal.json` 核查整包文件变化。
哈希是本地一致性校验，不是签名、防篡改认证或真实执行证明；改动后重建新包，不覆盖旧包。

**不得从生成目录直接启动 agent。** 同级槽位、inputs 和用户级 skill/MCP 可能污染对比。
未来执行器只将一个槽位装入一个全新、可丢弃的隔离环境，给独立 verifier 另一个边界。
目录拷贝、Codex workspace-write 和现有进程监督器都不能代替安全隔离。
无 skill 是“不提供本次 workflow”，不是已证明 CLI 没有内建或用户级 skill。

## 尚未满足的启动门槛

1. 用户确认精确模型、CLI 版本、认证模式及 smoke 花费上限；不能假定免费或把订阅等同零成本。
2. 可丢弃隔离环境、独立 verifier、网络/工具规则，审计全局/项目配置与 skills/MCP；不暴露宿主凭据。
3. 实际可强制的超时/token/费用约束、取消和后代回收、原始 trace/stderr/进程退出/计费证据。
4. 冻结可运行执行计划及配置摘要；本 packet 不是 analysis_tools 预注册 plan。
5. smoke 后独立核验：候选哈希、验收器哈希、环境、命令/退出码、业务结果分别记录。
6. 实际结果导入必须验证真实性/身份；CLI complete 不能推导业务成功。失败、取消、缺失保留；
   未知耗时/费用继续 null，不能补零。合成、自检、真实模型三类不得混用。

当前工具即使 verify 通过也始终 `launch_supported: false`、`not_run`。不提供自动启动命令，
不声称真实端到端集成或隔离通过。不涉及前端、部署、推送或 PR。

原始真实 trace/stderr/计费材料可能包含密钥或隐私，默认仅本地保留；经审阅、脱敏并获授权前不得发布。

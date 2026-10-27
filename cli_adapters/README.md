# Codex CLI / Claude Code 离线适配层

**本阶段只生成计划、读取已有 trace、采集两份提交的差异。没有启动 agent 的入口。**
不调用模型、不读取用户认证、不安装软件、不上传文件，也不执行提交里的 Java/脚本。
真实端到端集成尚未测试；两个 JSONL 示例都是手工编写的 **SYNTHETIC TEST FIXTURE, NOT MODEL RESULTS**，不是模型成绩。

依赖 Python 3.10+ 标准库、POSIX 文件描述符与 `O_NOFOLLOW`；不宣称 Windows 兼容。
从仓库根目录执行：

```sh
python -m unittest discover -s cli_adapters -p 'test_*.py' -v
python -m cli_adapters --help
```

## 1. 只生成命令计划

先通过现有 `prepare` 流程准备独立工作目录；每个任务/模型/重复使用不同目录，不能共享先前对话或修改后的候选。
以下仅运行本地 Python 计划器，不会执行输出里的 `argv`：

```sh
python -m cli_adapters plan --provider codex \
  --workspace /tmp/my-independent-workspace \
  --model YOUR_EXPLICIT_MODEL --cli-version 0.164.0 \
  --auth-mode subscription --prompt-file /tmp/task-prompt.txt

python -m cli_adapters plan --provider claude \
  --workspace /tmp/another-independent-workspace \
  --model YOUR_EXPLICIT_MODEL --cli-version YOUR_INSTALLED_VERSION \
  --auth-mode subscription --prompt-file /tmp/task-prompt.txt
```

输出 `execution_status: not_run`、`business_status: not_evaluated`。没有 `run`、`execute`、任意附加参数、resume 或 import 会话选项。
模型和 CLI 版本必填但由调用者声明，计划器不探测版本、不解析移动别名。必须自行冻结精确模型、CLI、配置、技能、工作流与环境身份。
`auth_mode` 仅记录 `subscription` / `provider_api` / `unknown`，不接收密钥，不转换账单路线。

### 固定命令配置

- Codex：`codex -a never exec --json --ephemeral --sandbox read-only --cd WORKSPACE --model MODEL -`。
  `-` 明确从 stdin 读取提示词。修改任务需要明确指定计划器的 `--sandbox workspace-write`；默认只读计划不保证完成修复。
  **Codex 要求 Git 工作目录**，现有 `prepare` 产物未必有 `.git`。计划标为 `required_not_verified`；未来启动前，操作者应在独立候选目录准备专用 Git 仓库并确认边界。这里不执行 `git init`，不添加跳过 Git 检查的参数。
- Claude：`claude -p --input-format text --output-format stream-json --verbose --no-session-persistence --permission-mode dontAsk --model MODEL`。
  `cwd` 单独记录，提示词通过 stdin 字节传入，不拼接 shell 字符串。Claude 计划中的 sandbox 状态为 `not_configured_by_planner`；`dontAsk` 不是操作系统沙箱，也不保证所有写入动作可用。
- 提示词正文不写入计划，只有 UTF-8 字节数与 SHA256。现阶段没有实际发送 stdin；将来执行器必须按记录的哈希验证并传入原始字节。
- 不使用 `--dangerously-skip-permissions`、`--ignore-rules`、`--full-auto` 或权限绕过。`never` / `dontAsk` 是不询问策略，需要审批的操作可能失败。
- 不默认 `--bare`：Claude 此模式会影响 OAuth/订阅认证，且历史版本行为不同。没有该可选开关，因此不会偷偷切换认证/费用路线。
- 没有把 `--allowedTools` 当安全限制；本阶段不限制 Claude 的 MCP/插件/工具列表。安全执行环境仍是未来工作。

**改变 cwd 不等于隔离。** 用户/项目配置、规则、插件、技能、MCP、认证、环境变量、公开参考答案均可能影响结果。
计划将这些标为未检查，没有读取用户 home。独立目录的来源也不能由本工具认证；提示词/技能等实验变量应另存摘要并预登记。
没有时间/token/费用预算强制执行；不能据此声称不同 CLI 的预算已经等价。

## 2. 离线归一化已有 JSONL

```sh
python -m cli_adapters normalize --provider codex \
  --trace cli_adapters/fixtures/codex.synthetic.jsonl \
  --model synthetic-model --cli-version synthetic-version \
  --data-class synthetic_test_fixture
python -m cli_adapters normalize --provider claude \
  --trace cli_adapters/fixtures/claude.synthetic.jsonl \
  --model synthetic-model --cli-version synthetic-version \
  --data-class synthetic_test_fixture
```

仅支持 Codex `exec --json` 事件与 Claude `print stream-json` 事件，不兼容自制 transcript、SDK 任意导出格式或网页聊天记录。
默认数据类别 `unverified_external_trace`，不能传 `actual_agent_trials`。原始字节哈希保留；调用者应另行保存原始文件，本工具不重写它。

- 终态事件不证明 CLI 进程正常退出。`process_exit_code: null`、`process_status: not_supplied`、`cli_outcome_basis: terminal_event_only` 明确表示没有观测进程退出；本工具不启动或探测进程。
- CLI 完成/失败与任务正确性分离：`cli_outcome` 为 `completed` / `failed` / `incomplete`；`business_status` 始终 `not_evaluated`。
- Codex 只读取 `turn.completed` / `turn.failed`；普通 `error` 不等同于已知终态。Claude `result` 必须有字符串 `subtype` 与布尔 `is_error`；只有 `success` 且 `is_error: false` 才记完成。
- 相同终态重传只计一次并告警；不同终态、多轮/多会话拼接、终态后仍有其他事件报歧义错误，不自行挑有利的结果。
- 只采信终态 `usage`；忽略 assistant/stream 的局部或累计用量，不与 `modelUsage` 再求和。Codex 缓存命中是 input 子集；Claude 缓存读/写是单独类别。缺失项为 `null`，不补零。
- Codex 不推算 USD。Claude 仅保留 `total_cost_usd`；这是 CLI 报告估计值，不是订阅实际账单或已验证费用；有值时明确标为 `cost_semantics: cli_reported_estimate_not_verified_billing`，缺失时为 `unknown_not_reported`。缺失成本为 `null` 并提供原因。CLI duration 不冒充外部 wall time。
- 未知事件类型告警；未知字段不解释，终态字段保留在 `terminal_metadata`，所有原字段仍存在原始 trace 中。畸形 JSON、重复键、负数/非有限 token 或费用失败关闭。
- 原始 trace、`terminal_metadata`（可能有回答文本）、提交差异可能含敏感内容；在本地检查和脱敏后再考虑任何分享。本工具无自动上传功能。

与 `analysis_tools` 的后续接点：结果提供 `raw_trace_sha256`、`cost_usd` / 原因、`elapsed_seconds` / 原因及身份字段，但 `run_kind` 是 `offline_trace_normalization`，`analysis_record_ready: false`。
**不能直接冒充 `agent_trial`**。还需真实尝试证据、预登记 slot、确切环境/工作流、外部计时、验收输出哈希和独立的任务判定；不能用 CLI 的 completed 自动生成任务 success。

## 3. 提交 manifest / diff

在运行前保留一份不可变候选副本；运行后提供另一份独立副本。请选择本题要求提交的文件根目录，不要把用户 home、认证目录或整个开发环境作为输入。

```sh
python -m cli_adapters collect \
  --before /tmp/submission-before --after /tmp/submission-after
```

两目录不能相同或嵌套。输出每个文件的相对路径、字节数、SHA256，以及排序 manifest 的源哈希；修改/新增/删除记录包含前后哈希、可读文本 unified diff 及 diff 哈希。
二进制/非 UTF-8 或过大的文本只给哈希和说明，不伪造文本 diff。空目录和时间戳不计入源哈希。
输入不能包含任何符号链接、FIFO/设备等特殊文件；逐层使用目录描述符与 `O_NOFOLLOW` 防止路径跳出。
单文件最多 1 MiB、总内容最多 16 MiB、文件最多 2000、目录深度最多 32；文本 diff 合计最多 200000 字符/10000 换行符。
会检查读取期间的明显文件变化，但不是一致性文件系统快照或恶意并发写入防护。采集前必须停止写入，最好保留不可变副本。
源码只读取，不运行、不上传；采集不表示任务通过。

## 核验依据与边界

2026-10-27 核验：Codex 本机 `0.164.0` 的 `exec --help` 支持本计划所用参数（帮助命令不是模型调用）；Claude 本机未安装，仅核对官方文档/协议。**没有实际 agent 端到端集成证据。**

- [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive)
- [Codex exec event definitions](https://github.com/openai/codex/blob/main/codex-rs/exec/src/exec_events.rs)
- [Claude headless mode](https://code.claude.com/docs/en/headless)
- [Claude CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude official SDK message parser](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/message_parser.py)

协议会变化，以上在线链接并非不可变版本锁。计划记录调用者声明版本和当前配置 ID，实际启用前必须核对对应版本，不应把未验证的后续版本当已兼容。

CLI 成功输出 JSON 时退出 0（不代表 trace 完成或任务通过），输入/文件错误退出 1，参数错误退出 2。只写 stdout/stderr，不自动保存文件；如重定向输出，应使用新的本地路径，避免覆盖原始证据。

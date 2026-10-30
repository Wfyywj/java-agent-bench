# 离线实验工作区（Codex CLI / Claude Code）

把任务准备、独立提交目录、命令计划和证据缺口串成一个入口。**不会运行模型、联网、登录、读取凭据、执行候选代码或估算费用。** 仅 Python 3.10+ 标准库，POSIX/Linux/macOS；Windows 未支持（沿用 adapter 的 `O_NOFOLLOW` 文件检查）。无需安装包，从仓库根运行。

## 可执行快速指南

下面创建本地离线示例；`example-model-id` / `example-cli-version` 是显式占位，不是已验证型号或版本。之后真正实验前应换成你实际确认的精确标识，并重新创建工作区。

```sh
python3 -m experiment_tools doctor --provider codex
# mktemp 仅创建父目录；init 要求目标 run 尚不存在。
PARENT=$(mktemp -d)
python3 -m experiment_tools init \
  --task B01-slice --provider codex \
  --model example-model-id --cli-version example-cli-version \
  --auth-mode unknown --sandbox workspace-write \
  --workspace "$PARENT/run"
python3 -m experiment_tools status --workspace "$PARENT/run"
cat "$PARENT/run/GUIDE.md"
```

Claude Code 示例（另一个全新目录）：

```sh
python3 -m experiment_tools doctor --provider claude
PARENT_CLAUDE=$(mktemp -d)
python3 -m experiment_tools init \
  --task B01 --provider claude \
  --model example-model-id --cli-version example-cli-version \
  --auth-mode unknown --workspace "$PARENT_CLAUDE/run"
python3 -m experiment_tools status --workspace "$PARENT_CLAUDE/run"
```

`--task` 接受实际实现的任务 ID（例如 `B01`）、implementation ID（`B01-slice`）或 `S04-spring`。可用任务见 `python3 scripts/engineering.py list`。尚未实现的任务拒绝初始化。`--auth-mode` 仅记录 `unknown|subscription|provider_api` 声明，不探测认证与计费。

## 创建了什么

| 文件/目录 | 用途 |
|---|---|
| `baseline/` | allowlist 准备出的原始提交快照；不要修改 |
| `candidate/` | 独立复制，无共享硬链接；只让 agent 编辑这里 |
| 外层 `PROMPT.md` | 交给 CLI stdin 的简短任务指引；实际任务说明在 candidate/PROMPT.md 中 |
| `command-plan.json` | 复用 `cli_adapters.plan` 的 argv/cwd/stdin 哈希和安全限制；**没有执行** |
| `next-steps.json` | 手工 Git 准备、归一化、差异收集、可信评估、状态检查的结构化计划 |
| `GUIDE.md` | 当前工作区具体路径的中文命令指南 |
| `manifest.json` | 明确 task/implementation、原 task manifest SHA256、声明配置、快照/计划哈希；费用为 null |

baseline 是起始代码，**不是 A/B 实验里的另一个模型对照臂**。本 manifest 不是 `analysis_tools` 的预注册分析计划；配对实验还需独立冻结臂配置、预算、重复、分配和结果/费用口径。不要把初始化或本地测试包装成真实 agent trial。

## 手动运行前的必要检查

1. `doctor` 只查看 PATH 中是否存在 `python3/java/javac/git/codex/claude`；不启动它们，也不会读 HOME 配置、认证或环境变量中的密钥。检查结果不是认证、版本或运行就绪证明。Java 21、CLI 版本和各参数必须另行确认。`javac` 缺失仅代表 PATH 无该命令，不排除 `java -m jdk.compiler` 可用。
2. Codex 需要 Git 仓库。生成的 GUIDE 有明确 `git -C /.../run init` 命令；本工具不会自动执行。仅在决定以后运行时手工执行，不能在 benchmark 根目录误执行。外层 `.git` 不进入 baseline/candidate 收集快照；candidate 会识别父目录仓库。baseline 与 candidate 同处该 Git 工作区，不是安全隔离；不要让 agent 修改 baseline。
3. Codex 默认 `--sandbox read-only` **不能写修复**；需要修复时如快速指南用 `--sandbox workspace-write` 初始化。Claude 不支持这个 Codex sandbox 参数；Claude 只能使用接口默认 `read-only`，但它**不表示 Claude 已被设置为只读或沙箱化**，计划明确记录 `not_configured_by_planner`。
4. 本工具故意没有自动启动 agent 的 shell 脚本。审查计划中的 argv、cwd、stdin 和本机插件/规则/工具权限，再决定是否手动执行。执行时保留未经编辑的 `trace.jsonl`。工作目录隔离不隔离用户级配置、MCP、skills、认证或公开答案；未强制预算、token、费用上限。
5. 有真实 trace 后按 GUIDE 运行 normalize / collect。只有信任候选代码时才运行带 `--trusted-code` 的 evaluate；评估**不是沙箱**。不要在不可信提交上直接运行。
6. `status` 列出 `trace.jsonl`、`normalized-trace.json`、`collection.json`、`evaluation.json` 的缺失/空/存在未验证状态；提供快照与计划的变化提示。即使所有文件存在且声称通过，也保持 `business_status: not_evaluated`、费用未知，不能据此声称真实模型成功。

## 安全与接口约定

- stdout 是 JSON；成功（含证据尚不完整的 status）退出 0，参数/输入/文件错误退出 2，错误 JSON 在 stderr（argparse 参数错误是常规文本）。
- 目标父目录必须已存在；目标目录/文件不得存在。拒绝仓库内部目标、`..`、反斜杠、控制字符、符号链接路径。未准备成功会清理本次新建目录。不得在同一目标并发执行初始化或让不可信进程修改工作区。
- 使用现有 `engineering.prepare` allowlist，不复制 reference/verifier；公开仓库本身仍可访问，不是保密测试。仅面向受信本地仓库/文件，初始化拷贝过程不承诺对抗并发目录替换攻击。
- status 仅读取固定文件名及限定快照，拒绝符号链接/特殊文件/过大文件，manifest 使用严格 JSON 解析。manifest 未签名，可由本地人改写，哈希不证明来源真实性；不会信任文件中的 `passed` 或费用字段。
- 工作区计划使用绝对路径，搬迁后 status 拒绝继续；请新建工作区而不是盲用旧命令。测试/分析程序不会自动上传或发布任何内容。
- 命令计划来自 `cli_adapters` 的已记录契约；这里没有新做真实 Codex/Claude 调用、认证验证或计费测试。`doctor` 的缺失工具不会阻止离线初始化。

## 测试和可信 fixture smoke

```sh
python3 -m unittest discover -s experiment_tools -p 'test_*.py' -v
# 全程离线，仅测试现有 synthetic fixture 的连接，不代表模型结果：
python3 -m experiment_tools doctor
PARENT_SMOKE=$(mktemp -d)
python3 -m experiment_tools init --task B01 --provider codex \
  --model fixture-model --cli-version fixture-version --workspace "$PARENT_SMOKE/run"
python3 -m cli_adapters normalize --provider codex --model fixture-model \
  --cli-version fixture-version --trace cli_adapters/fixtures/codex.synthetic.jsonl \
  --data-class synthetic_test_fixture > "$PARENT_SMOKE/run/normalized-trace.json"
python3 -m cli_adapters collect --before "$PARENT_SMOKE/run/baseline" \
  --after "$PARENT_SMOKE/run/candidate" > "$PARENT_SMOKE/run/collection.json"
python3 -m experiment_tools status --workspace "$PARENT_SMOKE/run"
```

该 smoke 没有 trace 原件和 evaluator 证据，status 应继续显示它们缺失。测试覆盖双 CLI、实现 ID、独立副本、覆盖/路径穿越/符号链接拒绝、失败清理、manifest 篡改、缺失/伪成功证据和不启动进程的 doctor。

## 阶段 B：明确标记的合成 Recipe 闭环

新增 [RECIPE.md](RECIPE.md)：`python3 -m experiment_tools.recipe` 提供
example → freeze → 独立 A/B 工作区 → synthetic replay envelope → 严格分析。
仅 B01 合成数据契约回放，不启动 agent 或 Java evaluator；不接收真实/参考解证据。
全部槽位（含 missing / 开始前 cancelled）保留，未知成本/耗时为 null。
页面接口尚待接入，当前网站 importer 不支持该展示 fixture。

## B02/S01 workflow pilot 启动前材料

[离线 pilot packet](PILOT.md) 提供一个 B02 smoke 与 12 个正式对比预留槽位，
锁定六阶段用户 workflow 文本及相同任务输入。全部标记 NOT_RUN；不是模型执行器或结果。

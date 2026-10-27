# 从选题到查看证据

这一版把日常入口收敛为网站和一个离线工作区工具。没有后台模型执行、自动扣费或真实模型排行榜。

## 1. 下载项目

```sh
git clone https://github.com/Wfyywj/java-agent-bench.git
cd java-agent-bench
python3 -m experiment_tools doctor --provider codex
```

使用 Claude Code 时把 provider 改为 `claude`。doctor 检查本机工具是否可找到，不登录、不读取认证配置，也不保证 CLI 版本兼容。需要 Python 3.10+；验收 Java 题需 Java 21+。Node 用于网站单元测试，不是准备工作区的前提。

B01 是不依赖外部数据库的起步切片。S04/S05 及 S04-spring 的依赖需通过各题说明的 checksum 固定下载流程准备；不能把整库描述为完全不需要联网。

## 2. 选择可执行变体

网站上的“场景设计”描述完整目标，“工程切片/集成变体”才是当前可执行范围。优先选 B01-slice 熟悉流程，再按需要选择更难题。青铜到王者是设计分档，不是已实测校准的模型等级。

```sh
python3 scripts/engineering.py list
python3 -m experiment_tools init --help
```

init 要求显式填写任务、provider、模型 ID、CLI 版本和仓库外的新目录。网站引导可生成命令，但不会代替你执行。不要把示例名称当真实模型 ID。

## 3. 创建独立实验目录

根据实际安装的工具填写参数，例如：

```sh
python3 -m experiment_tools init \
  --task B01-slice --provider codex \
  --model YOUR_EXACT_MODEL_ID --cli-version YOUR_INSTALLED_CLI_VERSION \
  --workspace /tmp/jab-b01-control --sandbox workspace-write
```

这里的模型、版本是操作者声明，并非自动验证。不要原样执行仍含 `YOUR_...` 的示例。Claude 使用 `--provider claude`，不能把 Codex 的 sandbox 模式视为 Claude 的隔离保证。

目录包含 baseline、candidate、题面、计划、manifest 与操作指南。已有目录不会被覆盖。工具只准备材料，执行前阅读生成的 GUIDE.md 与 command-plan.json：先确认认证来源、预算、权限、专用 Git 工作区和隔离环境。

默认 read-only 计划不能修复文件；实现任务需要你主动选择 workspace-write 并承担对应权限。即使分目录、使用 Git 或 CLI 的权限开关，也不构成完整防泄漏/恶意代码安全边界。

## 4. 在批准的环境完成任务，再验收

这一步由你在确定模型、配置、认证和预算后使用自己的 CLI 完成。当前工具不启动 CLI、不获取密钥、不自动调用模型。记录实际工具版本、调用参数、退出码、耗时和完整原始证据；不要把 CLI 的 terminal event 当业务通过。

```sh
python3 -m experiment_tools status --workspace /tmp/jab-b01-control
```

候选代码必须审查并被你信任，才能使用本地验收器；它会运行 Java 代码，不是沙箱：

```sh
python3 scripts/engineering.py evaluate B01 /tmp/jab-b01-control/candidate \
  --trusted-code --output /tmp/jab-b01-control/evaluation.json
```

不要为了消除提示而盲目加 `--trusted-code`。对于任意不可信候选，应先建设受限、可丢弃的隔离执行环境。验收输出放在 candidate 之外，避免改变提交身份。

## 5. 导入与复盘

在网站“结果与证据”导入 evaluation.json。先看任务身份、manifest 版本、严格通过状态和失败细节。文件导入并不认证来源，参考解自检也不是模型成绩。未测费用保留未知，不能填零。

真正比较 skill 或工作流时，保持模型与其他条件相同，以全新的独立工作区运行 A/B，提前登记题目与重复次数，保留失败、缺失和基础设施错误。正式配对分析仍使用 [analysis_tools](../analysis_tools/README.md) 的严格计划与记录格式；普通验收 JSON 不能直接当作完整 agent trial。

## 维护者：一个命令检查工具

```sh
python3 scripts/check_fast.py
```

该命令覆盖目录生成、Python 工具测试、JavaScript 语法与网站 DOM-stub 单测。它不会调用模型；也不等于浏览器视觉测试或完整 Java 工程题自检。全题检查另外执行 `python3 scripts/check_engineering.py`，先按说明准备固定依赖。

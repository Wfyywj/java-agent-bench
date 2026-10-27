# Java Agent Bench

面向 Java 服务端的分级工程测评实验室，用于比较模型、Skills 与工作流。**v0.2 是开发预览，不是已校准的模型排行榜。**

网站：[工程测评实验室](https://java-agent-bench-lab.sound-acorn-0952.chatgpt.site)（当前仅所有者可访问，不是公开站点）。

## 目前真正完成了什么

- 25 个原创复杂场景设计，青铜/白银/黄金/钻石/王者各 5 题；覆盖需求澄清、跨仓库定位、实现、测试、Review、事故诊断。全部标记 `design_only`。
- 25 个限定范围的可运行工程切片（见 `engineering/`），实际 CLI/HTTP/文件或 H2 流程；不是完整分布式场景。每题有原始缺陷、参考修复、独立验收与故意错误的语义变体。
- 额外的 S04-spring 真实 Spring 事务集成变体，实际使用 @Transactional/CGLIB、JDBC/H2，不宣称 PostgreSQL 等价。
- 3 个独立可执行 Java 机制任务：租户支付幂等、并发库存预留、Outbox 租约重试。它们是内存模型，不是完整 Spring/MySQL 生产工程，也不冒充前述 25 题的实现。
- Python 标准库验收内核：净构建、限时、限输出、补丁哈希、环境证据、结构化结果。
- 任务浏览与详情、实验计划导出、结果 JSON 导入、协议和路线图网站。
- **没有调用被测模型，没有模型排名，没有难度实测校准。**

## 快速开始

要求 Python 3.10+、Java 21+（含 jdk.compiler）。无 Maven/网络依赖。

```sh
python3 -m unittest discover -s tests -v
node --test tests/test_web.mjs
python3 scripts/engineering.py list
python3 scripts/engineering.py prepare B01 /tmp/b01-work
# 修改 src 与本题要求的结构化产物，仅对可信代码执行下步
python3 scripts/engineering.py evaluate B01 /tmp/b01-work --trusted-code --output /tmp/b01-result.json
python3 harness/bench.py selfcheck R01
python3 harness/bench.py prepare R01 /tmp/r01-work
# 在 /tmp/r01-work/src 中修复可信代码
python3 harness/bench.py evaluate R01 /tmp/r01-work/src --output /tmp/r01-result.json
```

`prepare` 不复制参考答案与验收器，但它们在公开仓库中仍然可见。这不是防泄漏隔离。**当前执行器仅适用于可信代码，不是安全沙箱。不得直接运行任意模型或第三方生成的不可信代码。** 详见 [执行边界](harness/INTEGRITY.md)。

## 文件地图

- `catalog/tasks.json`：25 道设计稿的唯一数据源。
- `tasks/R01..R03/`：原始缺陷、参考修复、验收器与错误变体。
- `harness/bench.py`：执行入口。
- `harness/results/`：真实参考解/缺陷/变体自检证据，不是 AI 分数。
- `engineering/`：25 个任务的工程切片及明确覆盖边界。
- `scripts/engineering.py`：统一 prepare/evaluate 入口，结果可导入网站。
- `dist/`：无构建依赖的静态网站。
- `docs/TASK_DESIGN.md`：任务设计协议。
- `docs/RESEARCH.md`：开源测评经验和来源。
- `docs/ROADMAP.md`：可执行里程碑与验收门禁。

## 公平比较

固定题目版本、预算、模型或工作流，做配对实验；模型榜与系统榜分开。严格成功率、时间、费用、回归、维护性分别报告。公开开发集可能被模型见过，不应声称“无污染”。段位是设计标签，需后续基线实测校准。

## 许可证

沿用仓库所有者创建的 MIT LICENSE。当前题目与实现为原创；上游项目只作研究引用，没有把其代码/题目自动纳入 MIT 范围。引入外部任务时必须逐项记录来源、提交和原始许可证。

## 验证与 CI

本地运行 `python3 scripts/check_engineering.py` 可执行全部已存在切片的可信自检。S04/S05 的 H2 依赖从 Maven Central 按固定版本与 SHA256 获取，不随仓库分发。GitHub Actions 配置只在 main 推送或手动触发运行，不提交密钥；CI 状态以具体提交的实际运行结果为准。

候选任务 ZIP 可在网站任务详情下载；仓库不提交生成包，运行 `python3 scripts/build_implementations.py && python3 scripts/build_task_packages.py` 可重建。不会在包中复制评分器或参考答案，但公开仓库依然可访问，不能当成防泄漏隔离。

## 离线 A/B 分析

`analysis_tools/paired_analysis.py` 比较预先登记的真实 agent 试验，严格锁定版本与配置，保留失败、缺失和未知费用；不把参考解自检当模型成绩。示例全部明确标为合成测试夹具，默认拒绝作为真实记录。使用方法见 [分析工具说明](analysis_tools/README.md)。

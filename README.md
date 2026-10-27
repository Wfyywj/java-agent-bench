# Java Agent Bench

面向 Java 服务端的分级工程测评实验室，用于比较模型、Skills 与工作流。**v0.1 是开发预览，不是已校准的模型排行榜。**

## 目前真正完成了什么

- 25 个原创复杂场景设计，青铜/白银/黄金/钻石/王者各 5 题；覆盖需求澄清、跨仓库定位、实现、测试、Review、事故诊断。全部标记 `design_only`。
- 3 个独立可执行 Java 机制任务：租户支付幂等、并发库存预留、Outbox 租约重试。它们是内存模型，不是完整 Spring/MySQL 生产工程，也不冒充前述 25 题的实现。
- Python 标准库验收内核：净构建、限时、限输出、补丁哈希、环境证据、结构化结果。
- 任务浏览与详情、实验计划导出、结果 JSON 导入、协议和路线图网站。
- **没有调用被测模型，没有模型排名，没有难度实测校准。**

## 快速开始

要求 Python 3.10+、Java 21+（含 jdk.compiler）。无 Maven/网络依赖。

```sh
python3 -m unittest discover -s tests -v
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
- `dist/`：无构建依赖的静态网站。
- `docs/TASK_DESIGN.md`：任务设计协议。
- `docs/RESEARCH.md`：开源测评经验和来源。
- `docs/ROADMAP.md`：可执行里程碑与验收门禁。

## 公平比较

固定题目版本、预算、模型或工作流，做配对实验；模型榜与系统榜分开。严格成功率、时间、费用、回归、维护性分别报告。公开开发集可能被模型见过，不应声称“无污染”。段位是设计标签，需后续基线实测校准。

## 许可证

沿用仓库所有者创建的 MIT LICENSE。当前题目与实现为原创；上游项目只作研究引用，没有把其代码/题目自动纳入 MIT 范围。引入外部任务时必须逐项记录来源、提交和原始许可证。

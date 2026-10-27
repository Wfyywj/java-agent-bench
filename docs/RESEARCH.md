# 开源测评研究与设计取舍

核查日期：2026-10-27。只读来源研究，不代表运行过这些基准。

| 来源 | 借鉴点 | 使用边界 |
|---|---|---|
| [SWE-bench](https://github.com/SWE-bench/SWE-bench) / [Multilingual](https://www.swebench.com/multilingual) | 固定基线提交、修复补丁、失败转成功与必需回归；多语言集含 Java | Multilingual 300 题为九语言总量，不是 300 道 Java；主代码 MIT 不自动覆盖所有上游题源 |
| [Multi-SWE-bench](https://github.com/multi-swe-bench/multi-swe-bench) | Java 环境构建、Docker 与 JSONL 结果协议 | 主仓库 Apache-2.0，旧 env 仓库 MIT；不同版本统计不可混用 |
| [Harbor](https://github.com/harbor-framework/harbor) | 隔离任务执行与版本化环境；[ATIF](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md) 轨迹格式 | Apache-2.0；本项目尚未集成，不宣称已有容器隔离 |
| [SWE-bench Pro V2](https://github.com/scaleapi/SWE-bench_Pro-os/blob/main/v2/README.md) | 防止联网取答案、篡改缓存后虚高；干净环境重新应用补丁验收 | 不含 Java，借鉴协议而非作为本平台题源；数据仍受原仓库许可证约束 |
| [GitTaskBench](https://github.com/QuantaAlpha/GitTaskBench) | 区分环境可执行与最终业务交付 | 许可证未在本次研究确认，不复制代码 |
| [SlopCodeBench](https://github.com/SprocketLab/slop-code-bench) | 连续 checkpoint：在自己旧代码上承受需求演进 | 许可证未在本次研究确认，不复制代码；难度演进不等于人为延长题面 |

## 采用的协议

1. 发布每题前：参考解全过、缺陷版本失败、合理错误修复被检出、重复运行无已知抖动。
2. 正式模型执行与验收分离，只迁移允许的补丁到干净基线；禁止修改验收器、读取参考解、使用未批准网络。
3. 模型比较固定 scaffold，系统比较完整披露 workflow 与 skills；变更一个因素，做配对 A/B。
4. 把依赖/基础设施失败与业务失败、超时分开，不悄悄剔除失败运行。
5. 费用包括 planner/reviewer 子调用、重试、工具构建及沙箱成本；未知成本标 null，不填 0。
6. public-dev 与 sealed-test 按仓库/题族隔离，保留集不上传公开 GitHub 或静态网站。公开库无法保证未被训练污染。
7. 五档段位按服务数、状态空间、并发不变量、兼容性、故障恢复与需求阶段数暂定，再以人类耗时与多基线校准。
8. 不用少数题的平均分给模型下广泛结论；报告覆盖面、重复次数、配对差与任务级不确定性。

## 本版未完成

Harbor 适配、真正隔离的执行器、真实数据库/消息系统任务、私有保留题、成本采集与模型实测均未完成。网站只展示已存在的设计或本地机制证据，不制造排行榜。

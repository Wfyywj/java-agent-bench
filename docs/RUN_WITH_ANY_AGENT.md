# 用同一任务比较模型、Skill 或工作流

## 1. 先认识本版的能力边界

这是公开开发集。参考答案、验收器和错误变体都在公开仓库，不能证明模型未见过题目。当前工程任务为有限范围的可运行切片，不等于完整生产系统。正式模型排名需要独立保留集和隔离 runner；尚未实现。

## 2. 建立干净任务工作区

```sh
python3 scripts/engineering.py list
python3 scripts/engineering.py prepare B01 /tmp/b01-control
python3 scripts/engineering.py prepare B01 /tmp/b01-treatment
```

prepare 按 task-local `agent-files.json` 白名单复制 baseline 与公开材料，不把参考实现/评分器主动交给被测代理。目录必须在本仓库之外且不存在，防止覆盖已有工作。

**仅分目录不构成隔离**：同一主机上的代理仍可能读到原始仓库。不要把这套本地便利流程当作防作弊或安全沙箱。

## 3. 固定比较条件

记录精确模型 ID/version、推理设置、系统提示词、skill 文件哈希、工具版本、调用预算、时间预算、是否联网、任务实现/manifest hash。A/B 只改变一个因素。先在网站生成计划，再把相同题面分别交给两个独立会话。

对于 Review 任务，只提交题目要求的 review.json 等审查产物，不要求代理修代码；诊断任务还需结构化证据判断。以该任务公开 prompt 为准，不把参考答案发送给代理。

## 4. 只有可信代码才能用当前本地执行器

```sh
python3 scripts/engineering.py evaluate B01 /tmp/b01-control --trusted-code --output /tmp/b01-control-result.json
```

`--trusted-code` 是操作人确认代码可信的声明，不提供任何安全隔离。任意模型生成代码未经审查不能直接运行。正式实验应在受限、可丢弃环境中执行，并隔离代理和验收资产；不要带入凭据、个人文件或宿主 Docker socket。

输出包括实现 ID、manifest/submission 哈希、环境、耗时、退出状态、原始业务报告。当前不会自动测量 API 费用，null 表示未知；不会调用模型。

## 5. 查看结果

将结果 JSON 导入网站“结果与证据”。网站验证基本结构和当前任务身份，但不认证文件来源；导入数据可被人工修改，不能当可信签名成绩。

每题默认“关键不变量全部通过”才算成功，不能把 passing assertions/total 当跨题难度归一分数。不同 slice 版本不可直接混排。分段位显示只是设计复杂度，不是经模型成绩校准的能力等级。

## 6. 重复与分析

正式实验前先跑小规模 pilot，检查全满分、全零分和抖动。保留所有原始尝试与基础设施失败，分别统计任务级成功率、配对变化、耗时和成本。不要由参考解/缺陷自检成绩推断任何模型的能力。

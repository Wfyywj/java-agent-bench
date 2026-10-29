# 旧证据绿灯（F3 / 证据新鲜度）

审计：[能力实测 F3](../../../assessments/2026-10-28-capability-audit.md)（修改绑定源码后，旧的四门成功不得继续让目录显示 `gates_green`）。阶段标准：[TRUSTWORTHY_EXPERIMENTS.md](../../../TRUSTWORTHY_EXPERIMENTS.md) A2。历史证据保留，但不能冒充当前源码的本次成功。

这不是 Java 验收，也不重跑 M1。反例只检查目录提升：一次性副本里改绑定源码，再运行 `scripts/build_implementations.py`。

## 从干净克隆重跑

在仓库根目录：

```sh
python3 docs/acceptance/fixtures/directed-counterexamples/stale-gates-green/repro.py
```

预期进程退出码 **0**，标准输出含 `verdict: blocks`。驱动会：

1. 把仓库复制到临时目录（不改当前工作区的目录或 B02 证据）。
2. 确认副本里的 B02 证据指纹等于当前源码，且已登记的 `B02-slice` 为 `gates_green`。
3. 只在副本里应用 [`bound-source.patch`](bound-source.patch)：向 `engineering/bronze/B02/prompt.md` 追加一行。该文件在 B02 源码指纹包内，不是评分规则。
4. 在副本里运行 `python3 scripts/build_implementations.py`。

防御成立时：

| 检查 | 预期 |
|---|---|
| 构建退出码 | 0 |
| `B02-slice` `status` | `runnable_slice`，不是 `gates_green` |
| `gate_status` | `stale` |
| `catalog/tasks.json` 里 B02 的 `slice_implementation` | 不存在 |
| `engineering/bronze/B02/evidence/m1-four-gates.json` | 字节不变，`pass` 仍为 true |
| 其余原先绿灯 | 仍是 `gates_green` |

若 B02 在源码已变后仍是 `gates_green`，驱动退出 **1**，并打印 `verdict: still-fails`。`tests/test_m1_evidence_integrity.py` 的 `test_directed_stale_gates_green_repro_blocks` 会因此失败。

## 本分支输出摘录

```text
build_exit: 0
build_stdout: 26 candidate-adapter slices discovered; 5 gates_green; original catalog statuses remain design_only.
B02-slice: status=runnable_slice gate_status=stale
B02_slice_implementation: absent
historical_evidence_pass: True
evidence_bytes_unchanged: True
gates_green_before: B02-slice,G01-slice,G05-slice,S01-slice,S04-slice,S04-spring
gates_green_after: G01-slice,G05-slice,S01-slice,S04-slice,S04-spring
verdict: blocks
```

指纹由 `a2ce8d1d5726c61e8091507252dc101bb61f3d1fd7af0bd22d97a198b586e4eb` 变为 `f48b43f06bce438454bef46fc4aacf96b25ca70d03c025861cefb0ea71590c02`。结论：**blocks**。

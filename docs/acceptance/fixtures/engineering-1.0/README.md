# engineering-1.0 可信参考夹具

这些文件是本地 `scripts/engineering.py`（`schema_version` `engineering-1.0`）对 **仓库内 reference 源码** 的验收输出，或由该输出改出一个字段后的拒绝样本。

它们是可信参考实现结果，不是模型分数、模型成绩或已校准排行榜条目。记录里的 `model` 为 null，`cost_usd` 为 null。不要把 `passed: true` 读成任何模型的成绩。

| 文件 | 是什么 |
|---|---|
| `b02-trusted-reference.json` | B02 reference 源码的单条验收记录 |
| `s01-trusted-reference.json` | S01 reference 源码的单条验收记录 |
| `version-mismatch-batch.json` | JSON 数组。第一条是 B02 记录的副本，仅把 `manifest_sha256` 换成 B01-slice 的清单哈希；第二条是未改动的 S01 记录。用于确认整批版本不匹配时一条都不导入。它本身不是一次新的验收，也不是模型输出。 |

生成方式见同日验收记录。候选目录在仓库外，只放入对应 `reference/src`，再用 `--trusted-code` 验收。

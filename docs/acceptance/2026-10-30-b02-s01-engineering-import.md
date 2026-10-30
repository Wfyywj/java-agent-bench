# B02 / S01 工程结果浏览器导入验收（2026-10-30）

对应 [issue #3](https://github.com/Wfyywj/java-agent-bench/issues/3)。这是公开站上真实 Chrome 的文件选择、下载和硬刷新记录，补上 [2026-10-28 记录](2026-10-28-m0-browser.md) 当时没有现成 `engineering-1.0` 样本、因而没做的 B02 / S01 导入。没有改判分、分析规则、结果协议或核心执行器。没有重新部署公开站。

导入的两条记录是仓库 reference 源码的本地可信验收，**不是模型分数、模型成绩或已校准排行榜条目**。页面把它们标成「未认证」。`model` 为 null，`cost_usd` 为 null。

## 结论

公开站 https://java-agent-bench-lab.sound-acorn-0952.chatgpt.site/ 就是这次的线上目标。页脚写的是 `v0.3 · 开放开发阶段`。HTML、`app.js` 和样式里都没有「v7」字样，也没有嵌入 git SHA。浏览器实际取到的 `app.js` 与当前 `main` 的 `dist/app.js` 字节相同。

桌面 1280×800 和移动 390×844 上都通过：导入 B02 与 S01 两条可信参考结果、同一批再导入时跳过重复、导出备份与导入内容一致、保存后忽略缓存刷新能恢复、版本不匹配的整批被拒绝且已有记录不变。

**不关闭 #3，也不勾 `docs/ROADMAP.md`。** 2026-10-28 记下的公开站差距（任务详情原始键名、没有「切片支持范围」、B02/S01 manifest 落后）在这次取到的静态资源上已经不在。issue 自己的完成条件仍包括勾选 ROADMAP，并且 10-28 那份六视图、详情三种关闭、实验计划导出和 R 系列坏 JSON 清单今天没有整表重跑。

## 测试版本

| | 当前 main | 公开站 |
|---|---|---|
| 入口 | 本记录不把本地预览当验收对象 | https://java-agent-bench-lab.sound-acorn-0952.chatgpt.site/ |
| Git | `a2022a15e643f3ef4be7696adf2ccc433ae24ccf`（`origin/main`，2026-10-30 16:18 +0800，#21）。生成夹具时工作区干净 | 页面不提供 SHA |
| 页脚 | `dist/index.html` 为 `v0.3 · 开放开发阶段` | 同左。没有 v7 |
| 计数 | 与公开站相同的目录文件 | 原创场景 25，可执行变体 29，已完成模型实测 00 |
| `app.js` SHA-256 | `3127640bcf5c7d79598959ba2881c184c02624bc7075d282a014bc61d7ba341b`（64939 字节） | 浏览器响应相同 |
| `style.css` SHA-256 | `ae6009300629693553618ffc511d4139be613a6a506361904a30cccd4d3f744a`（11870 字节） | 相同 |
| `implementations.json` | `1b8339b7443b1d2c1a1d4f66a509ac7870897965b04b963647779fc2a8e821d7` | 相同 |
| `runnable.json` | `c7e1d65b4ff8697d90cda9753fd75528c6e6ca9e394e53d59df016d8bf1d7f2b` | 相同 |
| `tasks.json` | `54d3543d49825590021a1ed9f00cd6f348c6e0e23a8420cfdaa401273c17da5b` | 相同 |
| `index.html` | `9c71e75aa0a4aafb378f5a4a377b392fc1c470cccdf507fbe51fb736f4865530`（2166 字节） | 多出一段 Cloudflare challenge 脚本，正文与 `dist/index.html` 相同 |

B02-slice 与 S01-slice 的 `manifest_sha256` 公开站和当前目录都是：

| 变体 | manifest |
|---|---|
| B02-slice | `8a85b5f838361506ab14bf9c1b5182c7fa20e8ea475bba85a847bc64d66e374f` |
| S01-slice | `0e5da45d2cfab79fcf1abf870ebb9d53a7f99e01c6018a0dbe2df47f6d81eba6` |

这与 `engineering/bronze/B02/task.json`、`engineering/silver/S01/task.json` 的 SHA-256 一致。10-28 公开站上那两个旧 manifest 已经不在这次响应里。

## 环境

- 日期：2026-10-30 17:56–18:01（Asia/Shanghai）
- 操作系统：Linux 6.12.94+ x86_64
- 浏览器：Google Chrome 156.0.8078.47，有界面窗口，`DISPLAY=:1`。不是 headless 单元测试。用户代理里的版本号被缩成 `Chrome/156.0.0.0`
- 视口：桌面 1280×800；移动 390×844
- 每个视口单独的浏览器配置，避免 localStorage 串味
- 硬刷新用的是 Chrome DevTools `Page.reload` 且 `ignoreCache: true`（并关闭缓存），然后等目录计数变成 25，再打开「结果与证据」。不是只在内存里重绘

## 方法与夹具

夹具由公开启动器 `scripts/engineering.py` 写出，`schema_version` 为 `engineering-1.0`。先在仓库外 `prepare`（白名单复制的是 baseline，不是参考解），再对仓库外的 reference 候选执行 `--trusted-code`。候选目录只放入对应 `reference/src`，没有模型输出。验收输出写在候选目录之外。

```sh
python3 scripts/engineering.py prepare B02 /tmp/jab-accept-b02-prep
python3 scripts/engineering.py prepare S01 /tmp/jab-accept-s01-prep
# 候选在仓库外，src 来自 engineering/bronze/B02/reference/src
# 与 engineering/silver/S01/reference/src
python3 scripts/engineering.py evaluate B02 /tmp/jab-accept-b02-ref \
  --trusted-code --timeout 180 --output /tmp/jab-b02-engineering.json
python3 scripts/engineering.py evaluate S01 /tmp/jab-accept-s01-ref \
  --trusted-code --timeout 600 --output /tmp/jab-s01-engineering.json
```

两条都是 `passed: true`、`exit_code` 0、`model` null、`cost_usd` null。`candidate_files` 的哈希与 reference 源码字节一致。记录里的 `evaluator_provenance.git_head` 是上面的 `a2022a15…`，`working_tree_dirty` 为 false。`security` 为 `TRUSTED LOCAL CODE ONLY; NOT A SECURITY SANDBOX`。

| 文件 | 用途 |
|---|---|
| [fixtures/engineering-1.0/b02-trusted-reference.json](fixtures/engineering-1.0/b02-trusted-reference.json) | B02 可信参考。SHA-256 `fa7dc57a4d128b3148eddaee37499b045b61743e5d0b2d8b66fc279596309f23`（3055 字节）。`implementation_id` `B02-slice`，提交 `49c5f7dec32ed98cc640c195346c545468d316ea5e30b8609c5753100ca0ca9f` |
| [fixtures/engineering-1.0/s01-trusted-reference.json](fixtures/engineering-1.0/s01-trusted-reference.json) | S01 可信参考。SHA-256 `0f875655455523599f598aa87637ef611cc3e1cfab75b1e2babf7396f150e38a`（64436 字节）。`implementation_id` `S01-slice`，提交 `51c3895152e875afa7d8fe4873f89fa838ad8fda54258614246582c9d29e141b` |
| [fixtures/engineering-1.0/version-mismatch-batch.json](fixtures/engineering-1.0/version-mismatch-batch.json) | 拒绝样本，不是另一次验收。JSON 数组：第一条是 B02 记录的副本，只把 `manifest_sha256` 换成 B01-slice 的 `c41391568b038fe7684a1ea3bd4fcff8a13514b39f0292e51b316c513f2de54e`；第二条是未改动的 S01 记录。SHA-256 `9e3aa8418b7f46e0a4b65069f7080b52d794a39531c9dd7abeb11684ff7cbe87` |

说明见 [fixtures/engineering-1.0/README.md](fixtures/engineering-1.0/README.md)。`prepare` 出来的 baseline 工作区没有拿去 evaluate，避免把故意失败的起步代码写成这条通过记录。

## 用例

期望按当前页面文案：整批通过才导入，重复内容跳过，失败时「本批未导入任何记录，已有结果保持不变」。下表两个视口一致，除非另注。

### 导入可信参考

- 步骤：打开「结果与证据」，用文件选择器一次选中 B02 与 S01 两个 JSON。
- 期望：新增 2 条，跳过 0 条。行内是 B02-slice 与 S01-slice，状态 `passed · 未认证`，版本号是上表 manifest。页面不把它们叫成模型成绩。
- 实际：两个视口都是「整批导入完成：新增 2 条，跳过 0 条重复记录。尚未保存的记录刷新后会丢失，请保存或导出。」副标题是「本地验收记录，不是模型排行榜。」列表下方写着「参考解与故障基线是验收器自检，不是 AI 模型分数」。打开 B02 原始证据，标题为「原始验收证据 · 未认证」，正文含 `schema_version` `engineering-1.0`、`"model": null`、`TRUSTED LOCAL CODE ONLY`。行上的标签是「未认证」，没有单独的「可信参考实现」徽章；这个称呼写在本记录和夹具说明里。
- 结果：通过。
- 截图：[桌面导入](../../artifacts/browser-acceptance/public-eng-desktop-import-valid.png)、[桌面原始证据](../../artifacts/browser-acceptance/public-eng-desktop-evidence.png)、[model 为 null](../../artifacts/browser-acceptance/public-eng-desktop-evidence-model.png)、[移动导入](../../artifacts/browser-acceptance/public-eng-mobile-import-valid.png)、[移动两条记录](../../artifacts/browser-acceptance/public-eng-mobile-import-rows.png)。

### 重复导入

- 步骤：不刷新，再选同一个 B02 文件和同一个 S01 文件。
- 期望：仍为 2 条；跳过 2 条。
- 实际：两个视口都是「整批导入完成：新增 0 条，跳过 2 条重复记录。……」记录数 2，哈希未变。
- 结果：通过。
- 截图：[桌面](../../artifacts/browser-acceptance/public-eng-desktop-import-duplicate.png)、[移动](../../artifacts/browser-acceptance/public-eng-mobile-import-duplicate.png)。

### 导出

- 步骤：点「导出全部备份」。
- 期望：下载的内容就是刚导入的两条记录。
- 实际：两个视口都下载 `jab-evidence-backup.json`，70715 字节，SHA-256 `f6fdc81ae517e532a72fa6873041e96e5579a54aae2176e71af1d765ab9f7e1c`，两份文件字节相同。内容是 JSON 数组，元素顺序为 B02-slice、S01-slice。解析后与两个源文件逐字段、键顺序一致，`model` 仍为 null。它不是两个源文件的字节拼接：站点导出的是一个数组。
- 结果：通过。
- 文件：[桌面导出](evidence/engineering-1.0/export-public-eng-desktop.json)、[移动导出](evidence/engineering-1.0/export-public-eng-mobile.json)。

### 保存后硬刷新

存储键是 `jab-results-v1`。刷新后默认视图是任务实验室，要再打开「结果与证据」。

- 步骤：点「保存全部到此浏览器」，忽略缓存刷新，等 `#total` 为 25，再打开结果页。
- 期望：恢复 2 条，B02 与 S01 还在。
- 实际：两个视口都显示「已保存 2 条到此浏览器；建议导出备份。」刷新后是「已从此浏览器恢复 2 条未认证证据。」两条的 manifest 与提交哈希与导入时相同。保存进 localStorage 的数组解析后与源记录一致。
- 结果：通过。
- 截图：[桌面](../../artifacts/browser-acceptance/public-eng-desktop-reload-restored.png)、[移动](../../artifacts/browser-acceptance/public-eng-mobile-reload-restored.png)。

### 版本不匹配整批拒绝

- 步骤：在已有 2 条并已保存的状态下，导入 `version-mismatch-batch.json`。然后再做一次忽略缓存的刷新。
- 期望：整批拒绝；已有 2 条不变，包括已保存副本。
- 实际：两个视口都是「version-mismatch-batch.json：工程切片结果标识、状态或证据格式无效。本批未导入任何记录，已有结果保持不变。」记录仍是原来的 B02 与 S01，localStorage 字符串与拒绝前相同。文案没有单独写出「manifest 不一致」；失败落在工程结果校验的同一句里。再次硬刷新后仍是「已从此浏览器恢复 2 条未认证证据。」这次画面与上一张恢复截图字节相同，不重复存放。
- 结果：通过。整批没有放进第二条本来合法的 S01。
- 截图：[桌面](../../artifacts/browser-acceptance/public-eng-desktop-version-mismatch.png)、[移动](../../artifacts/browser-acceptance/public-eng-mobile-version-mismatch.png)。

### 10-28 公开站差距抽查

只抽查当时失败的 B01 详情，用来判断公开站是否还落后，不是把整份 M0 清单重跑一遍。

- 实际：桌面和 390px 的 B01 对话框都有「切片支持范围」，以及「失败情形」「容易漏掉的陷阱」「必须守住的不变量」「核心失败判定」。正文里没有 `failureCases`、`traps`、`invariants`、`criticalFailurePolicy` 这四个键名。切片列表含 “CLI adapter verifies HTTP-compatible error value…”。
- 结果：与当前 main 的详情渲染一致。10-28 的那两项部署差距在这次公开站响应上已不在。
- 截图：[桌面](../../artifacts/browser-acceptance/public-eng-desktop-b01-detail.png)、[移动](../../artifacts/browser-acceptance/public-eng-mobile-b01-detail.png)。页脚 v0.3 见 [桌面落地](../../artifacts/browser-acceptance/public-eng-desktop-landing.png)。窄屏导航 `scrollWidth` 713、`clientWidth` 335，横向滚到「结果与证据」后可以点进结果页，见 [移动导航](../../artifacts/browser-acceptance/public-eng-mobile-nav-scrolled.png)。390px 下 `.asidefoot` 为 `display: none`，v0.3 仍在 DOM 里，画面上不显示。

### 控制台

这次两个视口的页面都没有应用脚本错误。公开站 HTML 末尾有 Cloudflare 注入的 challenge 脚本；会话没有被拦截页挡住。

## 未验证项

- 页面没有「v7」或构建号。若「v7」是站外对这次部署的叫法，本记录只能用上面的 URL 和 `app.js` 哈希指认，不能再对上一个 v7 标记。
- 没有重跑 2026-10-28 的整份交互清单：六视图逐个切换、详情的 × / Esc / 遮罩、实验计划空白与占位拒绝、真实计划下载、截断 JSON、R 系列根对象校验失败、R01 reference 导入。
- 没有 evaluate 或导入 B02 / S01 的 baseline。通过记录只覆盖 reference。
- 版本拒绝测的是一个 JSON 数组文件。没有另测「文件选择器里一个合法文件加一个非法文件」这种跨文件批次。
- 没有用 Ctrl+Shift+R 按键；硬刷新是 DevTools `Page.reload` `ignoreCache: true`。
- 没有测关掉浏览器配置再隔天打开，也没有测别的浏览器。
- 页面声明导入不做签名或来源认证。本记录没有把未认证记录当成已签名成绩。
- 没有屏幕录像放进仓库。
- 文件按钮显示浏览器自己的 “Choose Files”，不是站点文案。
- 没有重新部署，也没有改产品代码。

## 仍开放的事项

- #3 保持开放。ROADMAP M0「完整浏览器交互验收」没有在本变更里勾上。
- 公开站这次的应用脚本和目录 JSON 与 `a2022a15…` 的 `dist/` 一致，不再是 10-28 那份较短的 `app.js`。是否据此勾选 ROADMAP，仍要人看过本记录和 10-28 记录后决定。

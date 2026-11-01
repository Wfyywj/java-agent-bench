# M0 公开站浏览器交互验收（2026-11-01）

对应 [issue #3](https://github.com/Wfyywj/java-agent-bench/issues/3)。这是公开站上真实 Chrome 的点击、键盘、文件输入、下载和硬刷新记录，补上 [2026-10-28 记录](2026-10-28-m0-browser.md) 与 [2026-10-30 记录](2026-10-30-b02-s01-engineering-import.md) 当时写明没有在公开站整表重跑的部分。`node --test tests/test_web.mjs` 没有当作本记录的证据。没有改判分、分析规则、结果协议或核心执行器。没有重新部署公开站。

B02 / S01 的 `engineering-1.0` 可信参考导入**不在本次步骤里**。那部分沿用 [PR #23](https://github.com/Wfyywj/java-agent-bench/pull/23) 和 [2026-10-30 记录](2026-10-30-b02-s01-engineering-import.md)。本次 Chrome 取到的 `app.js` 与那次记录的 SHA-256、字节数相同，所以那份证据仍然指认这一份已发布脚本。

## 结论

公开站 https://java-agent-bench-lab.sound-acorn-0952.chatgpt.site/ 是这次的验收目标。页脚是 `v0.3 · 开放开发阶段`。页面没有嵌入 git SHA。Chrome 实际执行的 `app.js`、样式和三份目录 JSON 与当前 `main` 的 `dist/` 字节相同。

桌面 1280×800 和移动 390×844 都通过 issue #3 仍缺的交互项：六个指定视图可切换，B01 详情能打开并用 ×、Esc、遮罩关闭，风险区是中文标签并有「切片支持范围」，实验计划在空白、空字段和 #7 占位文字下拒绝下载，填完后下载的草案 `executable` 为 false、`cost_usd` 为 null，R 系列 `schema_version` 1.0 可以导入，坏 JSON 与校验失败不导入，重复记录跳过，未保存刷新会丢失，保存后硬刷新能恢复，源码链接正确，窄屏导航可横向滚动后点到后面的视图。

10-28 记下的公开站差距（风险区原始键名、没有「切片支持范围」）在这次对话框正文里不在。没有新的产品缺陷，没有另开 bug issue。

本变更勾上 `docs/ROADMAP.md` 里 M0「完整浏览器交互验收」这一行。不关闭 #3：下面的未验证项不是这次看到的故障，但是人看过两份公开站记录后再关 issue 更合适。

## 清单

| 项 | 桌面 1280×800 | 移动 390×844 |
|---|---|---|
| 六视图切换 | 通过 | 通过 |
| B01 详情、中文风险标签、「切片支持范围」 | 通过 | 通过 |
| 详情关闭：×、Esc、遮罩 | 通过 | 通过 |
| 实验计划：未选任务拒绝 | 通过 | 通过 |
| 实验计划：已选任务但字段为空拒绝 | 通过 | 通过 |
| 实验计划：#7 占位文字拒绝 | 通过 | 通过 |
| 实验计划：草案下载，`executable` false，`cost_usd` null | 通过 | 通过 |
| 坏 JSON 不导入 | 通过 | 通过 |
| 合法 JSON 但不是单次结果，校验失败 | 通过 | 通过 |
| R01 `schema_version` 1.0 导入，标「未认证」 | 通过 | 通过 |
| 同一条再导入，跳过重复 | 通过 | 通过 |
| 失败批次不冲掉已有记录 | 通过 | 通过 |
| 未保存就刷新，记录消失 | 通过 | 通过 |
| 保存后硬刷新，恢复 1 条 | 通过 | 通过 |
| 源码链接 | 通过 | 通过 |
| 移动导航可滚动并切换 | 桌面不需要横向滚动 | 通过 |
| B02 / S01 `engineering-1.0` | 不重跑，见 2026-10-30 | 不重跑，见 2026-10-30 |

## 测试版本

| | 当前 main | 公开站（本次 Chrome） |
|---|---|---|
| 入口 | 本记录不把本地预览当验收对象。`dist/` 用来对字节 | https://java-agent-bench-lab.sound-acorn-0952.chatgpt.site/ |
| Git | `94400918aff5216817f0e24d652df46794e2564f`（`origin/main`，#23 的文档提交）。`dist/` 相对 `a2022a15e643f3ef4be7696adf2ccc433ae24ccf` 无差异 | 页面不提供 SHA |
| 页脚 | `dist/index.html` 为 `v0.3 · 开放开发阶段` | 同左。DOM 文本含「不以演示数据冒充测评成绩」。没有 v7 |
| 计数 | 与公开站相同的目录文件 | 原创场景 25，可执行变体 29，已完成模型实测 00 |
| `app.js` SHA-256 | `3127640bcf5c7d79598959ba2881c184c02624bc7075d282a014bc61d7ba341b`（64939 字节） | Chrome 文档里的响应该哈希、该字节数 |
| `style.css` SHA-256 | `ae6009300629693553618ffc511d4139be613a6a506361904a30cccd4d3f744a`（11870 字节） | 相同 |
| `implementations.json` | `1b8339b7443b1d2c1a1d4f66a509ac7870897965b04b963647779fc2a8e821d7`（21277 字节） | 相同 |
| `runnable.json` | `c7e1d65b4ff8697d90cda9753fd75528c6e6ca9e394e53d59df016d8bf1d7f2b`（11531 字节） | 相同 |
| `tasks.json` | `54d3543d49825590021a1ed9f00cd6f348c6e0e23a8420cfdaa401273c17da5b`（176466 字节） | 相同 |
| `index.html` | `9c71e75aa0a4aafb378f5a4a377b392fc1c470cccdf507fbe51fb736f4865530`（2799 字节） | Chrome 重新加载后的文档响应与 `dist/index.html` 相同 |

另一次不用浏览器标识的 `curl` 取到的 HTML 是 3913 字节，SHA-256 `850797bd6ac8a15649edd33a590b5bedc472b217495cc8124755982a379f904c`，在 `</body>` 前多一段 Cloudflare challenge 脚本。验收以 Chrome 实际执行的文档为准，那份响应没有这段脚本。

`app.js` 哈希与 [2026-10-30 记录](2026-10-30-b02-s01-engineering-import.md) 相同。其后的 `94400918` 只记录了那次导入验收，没有改 `dist/`。

## 环境

- 日期：2026-11-01 16:20–16:35（Asia/Shanghai）
- 操作系统：Linux 6.12.94+ x86_64，`DISPLAY=:1`
- 浏览器：Google Chrome 156.0.8078.47，有界面窗口。用户代理把版本号缩成 `Chrome/156.0.0.0`。不是 headless，也不是 `tests/test_web.mjs`
- 视口：桌面 1280×800；移动 390×844。`devicePixelRatio` 为 1。布局宽度用 Chrome 的设备度量固定，截图就是该视口
- 每个视口单独的浏览器配置，避免 localStorage 串味
- 硬刷新是 Chrome DevTools `Page.reload` 且 `ignoreCache: true`（并关闭缓存），然后等 `#total` 变成 25，再打开「结果与证据」

窗口由本机的 Chrome 打开，点击、键入和截图走 Chrome DevTools。文件没有经过操作系统的文件选择窗口：本地路径交给 `#resultFile` 的是 DevTools `DOM.setFileInputFiles`，页面自己的 `onchange` 在浏览器里读取。这和点选同一份本地文件进入该输入框是同一条页面路径，但本记录没有把 GTK 文件对话框点开。

## 方法与夹具

导入用的成功文件来自仓库里已有的验收器自检，不是模型分数。没有新造 `engineering-1.0` 哈希，也没有重跑 `scripts/engineering.py`。

| 文件 | 用途 |
|---|---|
| `harness/results/R01-selfcheck.json` 的 `reference`，验收时写成带缩进的 JSON | 合法单次结果。SHA-256 `884691176acef90838861f0015e29103381f403ed12b35d9634b340243a1e221`（3126 字节）。`schema_version` 1.0，`task_id` R01，`task_version` 1.0.1，`status` `passed`。页面把它标成「未认证」 |
| 同一文件的根对象，文件名 `r01-selfcheck-wrapper.json` | 合法 JSON，但不是单次结果，用来触发校验失败。SHA-256 `c93c4c0d8c80c422bd3b857529a06a98e17cf0f9864fafb05d7e1b60d7062b7d` |
| [fixtures/truncated.json](fixtures/truncated.json) | 截断内容 `{"task_id": `，用来触发 JSON 解析失败。SHA-256 `8be625acec56e377a672d0698f6fbf899e079798d513dbeae9e2fd3caf206de2` |

B02 / S01 夹具仍是 [fixtures/engineering-1.0/](fixtures/engineering-1.0/README.md) 里已提交的两份可信参考。本次没有把它们再送进页面。

## 用例

期望按 issue #3 和当前页面文案。两个视口一致，除非另注。

### 源码链接

- 步骤：关掉 JavaScript 打开页面，读 `#repoLink`；再打开 JavaScript，等目录计数变成 25，重读。
- 期望：不依赖脚本即可打开 `https://github.com/Wfyywj/java-agent-bench`，文字为「GitHub 源码 ↗」，不出现「待连接」。
- 实际：两个视口在脚本关闭和打开后都是该 href 和该文字。HTML 里没有「待连接」。关掉脚本时，页面显示 noscript 说明，其中可见「源码与本地命令以 GitHub 源码为准」。
- 结果：通过。
- 截图：[桌面、脚本关闭](../../artifacts/browser-acceptance/public-20261101-desktop-repo-js-off.png)。390px 顶栏同样是「GitHub 源码 ↗」，见 [移动导航起点](../../artifacts/browser-acceptance/public-20261101-mobile-nav-start.png)。

### 六视图

- 步骤：依次点「快速开始 / 任务实验室 / 设计对照实验 / 结果与证据 / 评测协议 / 建设进度」。
- 期望：工作区标题分别为「从第一轮可复现实验开始」「任务实验室」「设计对照实验」「结果与证据」「评测协议」「建设进度」，对应导航按钮为当前项。
- 实际：两个视口全部如此。
- 结果：通过。
- 截图：桌面六张 `artifacts/browser-acceptance/public-20261101-desktop-view-*.png`（`start`、`catalog`、`planner`、`results`、`protocol`、`roadmap`）。

导航里还有第七项「合成演练」，不在 issue #3 列出的六个名字里。两个视口都点过，标题是「合成演练 · 只读槽位」，状态是「已只读打开冻结样本。夹具断言不是模型分数，也没有进入「结果与证据」。」来源写的是「站点副本 dist/samples/synthetic-replay-display-1.0.example.json」。这只说明该视图能打开已部署的冻结样本。合成演练的拒绝矩阵没有做，见未验证项。截图：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-view-synthetic.png)。

### 移动导航

- 步骤：390×844 下先把窗口滚回顶部，不滚动导航，测量按钮；再把导航滚到末端；然后点「建设进度」。
- 期望：六个指定按钮都能点到并切换视图。窄屏允许横向滚动。
- 实际：导航 `scrollWidth` 713、`clientWidth` 335。起点能完整看见「快速开始」「任务实验室」「设计对照实验」；「结果与证据」从左缘 340 伸到 444，只露出一条边。「合成演练」「评测协议」「建设进度」在首屏外面。滚到末端后 `scrollLeft` 约为 378，「合成演练」「评测协议」「建设进度」完整可见，「结果与证据」仍被裁成「与证据」。六个指定视图在滚入可视区域后都切换成功。点「建设进度」后，按钮为当前项，标题为「建设进度」。
- 结果：通过。导航可用。
- 截图：[起点](../../artifacts/browser-acceptance/public-20261101-mobile-nav-start.png)、[滚到末端](../../artifacts/browser-acceptance/public-20261101-mobile-nav-scrolled.png)、[点到建设进度](../../artifacts/browser-acceptance/public-20261101-mobile-nav-roadmap.png)。

390px 下 `.asidefoot` 为 `display: none`。v0.3 仍在 DOM 里，画面上不显示。这和 2026-10-30 记录相同。

### 任务详情与中文风险标签

- 步骤：在任务实验室打开 B01「查看任务」。再打开 S04，只读正文。
- 期望：对话框打开；可见「切片支持范围」和列表；风险区用中文标签「失败情形」「容易漏掉的陷阱」「必须守住的不变量」「核心失败判定」，而不是原始键名。
- 实际：两个视口的 B01 对话框都打开。正文同时含上述四个中文标签和「切片支持范围」，不含 `failureCases`、`traps`、`invariants`、`criticalFailurePolicy`。切片列表含 “CLI adapter verifies HTTP-compatible error value…”。S04 对话框含 `S04-spring`、「切片支持范围」和同样的四个中文标签，也不含那四个键名。S04 没有单独截图。
- 结果：通过。10-28 的公开站 #8 差距在这次响应上不在。
- 截图：
  - 顶部与关闭钮：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-detail-b01-top.png)
  - 切片范围：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-detail-b01-slice.png)、[移动](../../artifacts/browser-acceptance/public-20261101-mobile-detail-b01-slice.png)
  - 中文风险标签，含「核心失败判定」：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-detail-b01-critical.png)、[移动](../../artifacts/browser-acceptance/public-20261101-mobile-detail-b01-critical.png)

### 任务详情关闭

- 步骤：打开 B01 后，分别用 ×（`#closeDetail`）、Esc、遮罩点击关闭。每次关闭后重新打开。
- 期望：三种方式都使 `dialog.open` 变为 false。
- 实际：两个视口三种方式都关闭。遮罩点击落在视口 (8, 8)。该点在对话框矩形外，`elementFromPoint` 命中的是 `dialog#detail`，随后 `open` 为 false。
- 结果：通过。
- 截图：× 关闭后的目录 [桌面](../../artifacts/browser-acceptance/public-20261101-desktop-detail-closed-button.png)。

### 实验计划导出

表单里的名称、对照、实验组、模型 ID、重复次数、预算和种子是验收输入，用来确认导出，不是模型成绩。字段用键盘键入。

1. 空白导出
   - 步骤：打开「设计对照实验」，不填字段、不选任务，点「导出实验计划」。
   - 期望：不下载文件。
   - 实际：两个视口的字段都是空字符串，没有勾选。状态为「请至少选择一个任务。」下载目录为空。
   - 结果：通过。
   - 截图：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-plan-blank.png)、[移动](../../artifacts/browser-acceptance/public-20261101-mobile-plan-blank.png)
2. 已选任务但字段仍空
   - 步骤：只勾选 B01-slice，其余留空，再导出。
   - 期望：拒绝，不下载。
   - 实际：两个视口都是「名称、对照组、实验组或模型仍是占位或未填写。占位文字不能当作模型、对照组或实验组的取值。」没有下载。
   - 结果：通过。
   - 截图：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-plan-empty-fields.png)
3. 旧占位符（#7 回归）
   - 步骤：键入「新 Skill 配对实验」「baseline-no-skill」「workflow-v2」「请填写精确版本」，重复 3、预算 1800、种子 42，勾选 B01-slice，导出。
   - 期望：占位文字被拒绝，不下载。
   - 实际：两个视口都是上面同一句「占位或未填写」，字段仍是这些占位字，没有下载。
   - 结果：通过。
   - 截图：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-plan-placeholder.png)、[移动](../../artifacts/browser-acceptance/public-20261101-mobile-plan-placeholder.png)
4. 填完后的真实下载
   - 步骤：名称 `acceptance-draft-not-a-score`，对照 `control-workflow-a`，实验组 `treatment-workflow-b`，模型 ID `acceptance-model-id-not-a-run`，重复 2，预算 60，种子 7，勾选 B01-slice，点导出。
   - 期望：浏览器下载 `experiment-plan.json`；内容是不可执行的规划草案，`cost_usd` 为 null。
   - 实际：两个视口都下载了该文件名，1052 字节。状态为「已导出规划草案。不可执行，没有启动任何模型或任务。费用为空表示未知。」JSON 中 `schema_version` 0.1，`plan_kind` `planning_draft`，`execution_supported` false，`executable` false，`cost_usd` null，`cost_status` `unknown`，`execution_status` `not_run`，任务为 B01 / B01-slice，manifest `c41391568b038fe7684a1ea3bd4fcff8a13514b39f0292e51b316c513f2de54e`。两份文件除 `created_at` 外相同。
   - 结果：通过。
   - 截图：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-plan-exported.png)、[移动](../../artifacts/browser-acceptance/public-20261101-mobile-plan-exported.png)
   - 文件：[桌面](evidence/experiment-plan-public-20261101-desktop.json)（SHA-256 `1d04f0257e61399e8f34191c0baa6439228bc086c39e0c8c0a84130b3045bfaa`，`created_at` `2026-11-01T08:20:24.530Z`）、[移动](evidence/experiment-plan-public-20261101-mobile.json)（SHA-256 `e70986bb6f25fc22ae6588dc4974caa4f9f84dc4b234076bd501d616a7e59194`，`created_at` `2026-11-01T08:20:36.613Z`）

### 结果 JSON 导入

步骤都在「结果与证据」。文件只在浏览器内读取。B02 / S01 不在这张表里。

| 用例 | 步骤 | 期望 | 实际（两个视口一致） | 结果 |
|---|---|---|---|---|
| 坏 JSON | 选择 `truncated.json` | 解析错误；本批不导入；没有记录 | `truncated.json：Unexpected end of JSON input。本批未导入任何记录，已有结果保持不变。` 记录数 0 | 通过 |
| 校验失败 | 选择自检文件的根对象 | 与解析错误不同的校验文案；不导入 | `r01-selfcheck-wrapper.json：不是支持的单次验收结果：需要已知 R 系列任务与 schema_version 1.0。本批未导入任何记录，已有结果保持不变。` 记录数 0 | 通过 |
| 合法导入 | 选择 R01 reference | 新增 1 条，跳过 0 条；一行 R01，标「未认证」 | `整批导入完成：新增 1 条，跳过 0 条重复记录。尚未保存的记录刷新后会丢失，请保存或导出。` 行内为 R01、`passed · 未认证`、版本 1.0.1 | 通过 |
| 重复导入 | 再选同一个 reference | 仍为 1 条；跳过 1 条 | `整批导入完成：新增 0 条，跳过 1 条重复记录。…` 记录数 1 | 通过 |
| 失败不冲掉已有记录 | 已有 1 条时再导入截断文件 | 仍为 1 条，并说明本批未导入 | 记录数 1，文案含「已有结果保持不变」 | 通过 |

截图：[坏 JSON](../../artifacts/browser-acceptance/public-20261101-desktop-import-bad-json.png)、[校验失败](../../artifacts/browser-acceptance/public-20261101-desktop-import-validation.png)、[合法导入](../../artifacts/browser-acceptance/public-20261101-desktop-import-valid.png)、[重复](../../artifacts/browser-acceptance/public-20261101-desktop-import-duplicate.png)、[失败后仍保留](../../artifacts/browser-acceptance/public-20261101-desktop-import-bad-keeps.png)。移动宽度：[校验失败](../../artifacts/browser-acceptance/public-20261101-mobile-import-validation.png)、[合法导入](../../artifacts/browser-acceptance/public-20261101-mobile-import-valid.png)。

### 刷新恢复

存储键是 `jab-results-v1`。刷新后默认视图是任务实验室，要再打开「结果与证据」。

1. 未保存就刷新
   - 步骤：导入 reference 后不点「保存全部到此浏览器」，忽略缓存刷新，等计数变成 25，再打开结果页。
   - 期望：记录消失，回到空态。
   - 实际：两个视口都没有 `.resultrow`，列表是空态，`localStorage` 里没有 `jab-results-v1`。状态段落是空的，因为这时既没有导入消息，也没有恢复消息。
   - 结果：通过。
   - 截图：[桌面空态](../../artifacts/browser-acceptance/public-20261101-desktop-reload-unsaved.png)
2. 保存后刷新
   - 步骤：再次导入，点「保存全部到此浏览器」，忽略缓存刷新，等 `#total` 为 25，再打开结果页。
   - 期望：`已从此浏览器恢复 1 条未认证证据。` 且 R01 行还在。
   - 实际：两个视口的保存文案都是「已保存 1 条到此浏览器；建议导出备份。」恢复文案与 R01 行符合期望。保存的数组有 1 条，`schema_version` 1.0，`task_id` R01，`status` `passed`，`task_version` 1.0.1。
   - 结果：通过。
   - 截图：[桌面](../../artifacts/browser-acceptance/public-20261101-desktop-reload-restored.png)、[移动](../../artifacts/browser-acceptance/public-20261101-mobile-reload-restored.png)

### B02 / S01

不重跑。步骤、夹具哈希、重复跳过、备份导出、保存后硬刷新和版本不匹配整批拒绝见 [2026-10-30 记录](2026-10-30-b02-s01-engineering-import.md)。那次公开站 `app.js` 是 `3127640bcf5c7d79598959ba2881c184c02624bc7075d282a014bc61d7ba341b`（64939 字节），与本次 Chrome 响应相同。

### 控制台

这次两个视口没有应用脚本错误，也没有失败的文档请求。公开站有时会给非浏览器客户端注入 Cloudflare 脚本；本次 Chrome 文档响应与 `dist/index.html` 字节相同，会话没有被拦截页挡住。

## 缺陷清单

没有需要新开 issue 的产品缺陷。10-28 的公开站详情差距这次没有复现。测过不等于又修了一遍代码：本变更没有改页面。

## 未验证项

- 没有重跑 B02 / S01 可信参考导入、重复、备份导出、版本不匹配整批拒绝。沿用 2026-10-30 记录，且仅因为 `app.js` 字节相同才把那次结果算到这次部署上。
- 没有导入 R02、R03 的自检 reference。R 系列成功路径只覆盖 R01。
- 没有把「一个合法文件加一个非法文件」放进同一次多选。
- 没有点开操作系统的文件选择窗口。文件进入 `#resultFile` 的方式是 DevTools `DOM.setFileInputFiles`。
- 没有用 Ctrl+Shift+R。硬刷新是 DevTools `Page.reload` `ignoreCache: true`。
- 没有测关掉浏览器配置再隔天打开，也没有测别的浏览器。
- 没有点「GitHub 源码 ↗」跳转到仓库页面。核对的是 href、可见文字，以及脚本关闭时的 noscript 说明。
- 合成演练只确认视图能打开、冻结样本能只读显示。没有把 R 系列、工程结果、实验计划或坏 JSON 送进该页的拒绝路径。该页不是 issue #3 点名的六个视图，也不写入「结果与证据」。
- 没有导出 R01 的 `jab-evidence-backup.json`，没有做同版本对比，也没有删记录。
- 没有下载候选 ZIP，没有生成快速开始命令。
- 页面没有「v7」或构建号。本记录用 URL 和 `app.js` 哈希指认。
- 页面声明导入不做签名或来源认证。本记录没有把未认证记录当成已签名成绩。
- 屏幕录像不放进仓库。
- 文件按钮显示浏览器自己的 “Choose Files”，不是站点文案。
- 没有重新部署，也没有改产品代码。

## 仍开放的事项

- `docs/ROADMAP.md` 的 M0 浏览器验收一行在本变更里勾上。依据是公开站这次覆盖了 issue #3 的交互清单，B02 / S01 沿用同一 `app.js` 的 2026-10-30 记录。
- #3 不在本变更里关闭。未验证项里没有新的产品故障；关闭与否留给看过 [2026-10-30 记录](2026-10-30-b02-s01-engineering-import.md) 和本记录的人。

## 截图索引

目录：[artifacts/browser-acceptance/](../../artifacts/browser-acceptance/)。本次新增文件名以 `public-20261101-` 开头。桌面 1280×800，移动 390×844。早先 main 与公开站的截图仍留在同一目录，不覆盖。

# 用真实 GitHub 问题练习 Java 修复

从两种故障中选一个。GH01 练习 Gson 如何保留 JSON 数字 `-0` 的符号。GH02 练习 Resilience4j 停止重试时如何把原始异常传回调用方。[Gson 报告](https://github.com/google/gson/issues/1053) · [Resilience4j 报告](https://github.com/resilience4j/resilience4j/issues/1843)

## 准备并修复

需要 Python 3.10+ 和含编译器的 JDK 21+。从本仓库根目录或网站工具包解压后的目录运行以下命令。准备操作会从 GitHub 和 Maven Central 下载固定版本的文件并校验 SHA-256。工作区建好后即可断网练习。

```sh
python3 upstream/bench.py list
python3 upstream/bench.py prepare GH01 /tmp/gh01-work
python3 upstream/bench.py evaluate GH01 /tmp/gh01-work --trusted-code
```

第一次验收会显示上游缺陷触发的失败项。打开工作区的 `PROMPT.md`，按其中列出的路径修改 Java 源文件，再执行同一条 `evaluate` 命令。要做重试题，将两处命令中的题号换成 `GH02`，工作目录换成一个新路径。

退出码 `0` 表示通过，`1` 表示至少一项行为检查失败。`2` 表示验收未能正常完成，例如源码编译失败、依赖校验失败或目录与题号不符。

## 核对上游修复

```sh
python3 upstream/bench.py selfcheck GH01
python3 upstream/bench.py selfcheck GH02
```

自检在独立临时目录中下载并编译两个提交中的目标类，对两者运行相同的公开检查。每题的 `task.json` 给出原始 issue、修复 PR、许可证、源码提交和 JAR 校验值。独立验收程序位于同目录的 `Probe.java`。

验收覆盖题面列出的行为。依赖 JAR 提供该类周围的运行环境，本机 Java 进程会加载你修改后的类。请仅对已审查、信任的代码使用 `--trusted-code`。

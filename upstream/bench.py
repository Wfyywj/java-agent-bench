"""Prepare and evaluate a pinned upstream Java regression on trusted local code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

TASKS = Path(__file__).resolve().parent


def read_tasks():
    tasks = {}
    for manifest in sorted(TASKS.glob("*/task.json")):
        task = json.loads(manifest.read_text(encoding="utf-8"))
        if task["id"] != manifest.parent.name:
            raise ValueError(f"任务编号与清单目录不匹配：{manifest}")
        tasks[task["id"]] = task
    return tasks


def check_hash(path, expected):
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 校验失败：{path.name}（预期 {expected}，实际 {actual}）")


def download(url, dest, digest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=30) as response, dest.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    check_hash(dest, digest)


def jars(task, workspace):
    for dep in task["dependencies"]:
        yield dep, workspace / ".deps" / Path(urlsplit(dep["url"]).path).name


def fetch_sources(task, workspace, revision):
    commit = task[f"{revision}_commit"]
    for source in task["sources"]:
        path = source["path"]
        url = f"https://raw.githubusercontent.com/{task['repository']}/{commit}/{path}"
        download(url, workspace / path, source[f"{revision}_sha256"])


def prepare(task, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Reserve the path exclusively. A concurrent prepare must never overwrite it.
    dest.mkdir()
    try:
        for dep, jar in jars(task, dest):
            download(dep["url"], jar, dep["sha256"])
        fetch_sources(task, dest, "baseline")
        prompt = [
            f"# {task['id']} · {task['title']}", "", task["scenario"], "",
            f"问题记录：{task['issue_url']}", f"基线提交：{task['baseline_commit']}",
            f"上游许可证：{task['license']}（{task['license_url']}）",
            "", "## 需要修改的源码", "",
            *[f"- `{s['path']}`" for s in task["sources"]],
            "", "## 验收条件", "", *[f"- {item}" for item in task["acceptance"]],
        ]
        (dest / "PROMPT.md").write_text("\n".join(prompt) + "\n", encoding="utf-8")
        (dest / "PREPARED.json").write_text(
            json.dumps({"task": task["id"], "baseline_commit": task["baseline_commit"]}) + "\n",
            encoding="utf-8",
        )
    except BaseException:
        shutil.rmtree(dest)
        raise


def evaluate(task, workspace):
    workspace = workspace.resolve(strict=True)
    marker = json.loads((workspace / "PREPARED.json").read_text(encoding="utf-8"))
    if marker != {"task": task["id"], "baseline_commit": task["baseline_commit"]}:
        raise ValueError(f"工作区与 {task['id']} 的基线版本不匹配")
    dependencies = []
    for dep, jar in jars(task, workspace):
        check_hash(jar, dep["sha256"])
        dependencies.append(str(jar))

    sources = [workspace / source["path"] for source in task["sources"]]
    probe = TASKS / task["id"] / "Probe.java"
    javac = shutil.which("javac")
    compiler = [javac] if javac else ["java", "-m", "jdk.compiler/com.sun.tools.javac.Main"]
    with tempfile.TemporaryDirectory(prefix="upstream-build-") as build:
        cmd = [*compiler, "-proc:none", "-encoding", "UTF-8", "-d", build,
               "-cp", os.pathsep.join(dependencies), *sources, probe]
        compiled = subprocess.run(cmd, cwd=build, timeout=60)
        if compiled.returncode:
            raise ValueError("编译失败，请检查上面的编译器输出与 JDK 安装")
        # The dependency jars also contain the upstream classes. Ensure the patched
        # compilation units actually take precedence over those bundled classes.
        for source in task["sources"]:
            class_path = source["path"].split("/src/main/java/", 1)[1]
            if not (Path(build) / class_path).with_suffix(".class").is_file():
                raise ValueError(f"编译产物缺少待测类：{class_path}")
        classpath = os.pathsep.join([build, *dependencies])
        result = subprocess.run(["java", "-cp", classpath, "Probe"], cwd=build,
                                timeout=30, capture_output=True, text=True, errors="replace")
    print(result.stdout, end="", flush=True)
    print(result.stderr, file=sys.stderr, end="")
    checks = result.stdout.splitlines()
    failed = any(line.startswith("FAIL ") for line in checks)
    if result.returncode == 0 and not failed and any(line.startswith("PASS ") for line in checks):
        return True
    if result.returncode == 1 and failed:
        return False
    raise ValueError(f"验收程序未正常完成（退出码 {result.returncode}）")


def selfcheck(task):
    with tempfile.TemporaryDirectory(prefix="upstream-selfcheck-") as temp:
        workspace = Path(temp) / task["id"]
        prepare(task, workspace)
        print(f"基线 {task['baseline_commit']}", flush=True)
        if evaluate(task, workspace):
            raise ValueError("基线意外通过，未复现报告的缺陷")
        fetch_sources(task, workspace, "fixed")
        print(f"上游修复 {task['fixed_commit']}", flush=True)
        if not evaluate(task, workspace):
            raise ValueError("上游修复未通过验收")
    print(f"{task['id']} 自检通过：基线复现了缺陷，上游修复通过了相同的验收。")


def main():
    tasks = read_tasks()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="列出已收录的上游问题")
    for name in ("prepare", "evaluate", "selfcheck"):
        command = commands.add_parser(name)
        command.add_argument("id", choices=tasks)
        if name != "selfcheck":
            command.add_argument("workspace", type=Path)
        if name == "evaluate":
            command.add_argument("--trusted-code", action="store_true", required=True,
                                 help="确认在本机运行已信任的 Java 代码")
    args = parser.parse_args()
    if args.command == "list":
        for task in tasks.values():
            print(f"{task['id']}  {task['title']}  {task['issue_url']}")
        return 0
    task = tasks[args.id]
    try:
        if args.command == "prepare":
            prepare(task, args.workspace)
            print(f"{task['id']} 已就绪。题面：{args.workspace / 'PROMPT.md'}")
        elif args.command == "evaluate":
            return 0 if evaluate(task, args.workspace) else 1
        else:
            selfcheck(task)
    except (OSError, ValueError, URLError, subprocess.TimeoutExpired) as exc:
        print(f"{task['id']} 无法完成：{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

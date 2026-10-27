"""python -m cli_adapters: offline operations only; JSON goes to stdout."""
import argparse
import json
import sys
from .collection import collect
from .common import AdapterError, MAX_TRACE_BYTES, read_regular
from .normalize import normalize
from .plans import plan


def main(argv=None):
    parser = argparse.ArgumentParser(description="离线 CLI 计划/trace 归一化/提交差异；不执行 agent")
    commands = parser.add_subparsers(dest="command", required=True)
    planner = commands.add_parser("plan", help="仅生成计划，不启动 CLI")
    normalizer = commands.add_parser("normalize", help="只读取已有 JSONL")
    for command in (planner, normalizer):
        command.add_argument("--provider", required=True, choices=["codex", "claude"])
        command.add_argument("--model", required=True)
        command.add_argument("--cli-version", required=True)
    planner.add_argument("--workspace", required=True)
    planner.add_argument("--prompt-file", required=True)
    planner.add_argument("--auth-mode", choices=["subscription", "provider_api", "unknown"], default="unknown")
    planner.add_argument("--sandbox", choices=["read-only", "workspace-write"], default="read-only")
    normalizer.add_argument("--trace", required=True)
    normalizer.add_argument("--data-class", choices=["synthetic_test_fixture", "unverified_external_trace"], default="unverified_external_trace")
    collector = commands.add_parser("collect", help="只读取两份独立提交目录")
    collector.add_argument("--before", required=True)
    collector.add_argument("--after", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan(args.provider, args.workspace, args.model, args.cli_version,
                          read_regular(args.prompt_file).decode("utf-8"), auth_mode=args.auth_mode, sandbox=args.sandbox)
        elif args.command == "normalize":
            result = normalize(args.provider, read_regular(args.trace, MAX_TRACE_BYTES), model=args.model,
                               cli_version=args.cli_version, data_class=args.data_class)
        else:
            result = collect(args.before, args.after)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (AdapterError, OSError, UnicodeError) as exc:
        print("adapter error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

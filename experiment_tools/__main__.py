"""python3 -m experiment_tools: offline setup and evidence inventory."""
import argparse
import json
import sys
from .workspace import doctor, initialize, status


def main(argv=None):
    parser = argparse.ArgumentParser(description='离线实验工作区：不运行模型、不读凭据、不推断通过或费用')
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('doctor', help='检查 PATH 工具存在性，不启动任何 CLI')
    check.add_argument('--provider', choices=['codex', 'claude'])
    init = commands.add_parser('init', help='创建全新独立工作区和命令计划')
    init.add_argument('--task', required=True, help='B01 / B01-slice / S04-spring 等明确 ID')
    init.add_argument('--provider', required=True, choices=['codex', 'claude'])
    init.add_argument('--model', required=True)
    init.add_argument('--cli-version', required=True)
    init.add_argument('--workspace', required=True)
    init.add_argument('--auth-mode', choices=['subscription', 'provider_api', 'unknown'], default='unknown')
    init.add_argument('--sandbox', choices=['read-only', 'workspace-write'], default='read-only')
    show = commands.add_parser('status', help='检查快照和证据缺口，不判断业务成功')
    show.add_argument('--workspace', required=True)
    args = vars(parser.parse_args(argv))
    command = args.pop('command')
    try:
        result = {'doctor': doctor, 'init': initialize, 'status': status}[command](**args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

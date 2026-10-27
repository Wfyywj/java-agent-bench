#!/usr/bin/env python3
"""One repeatable entry point for offline tooling checks; no agent/model calls."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    commands = [
        [sys.executable, 'scripts/build_catalog.py'],
        [sys.executable, 'scripts/build_implementations.py'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'cli_adapters', '-p', 'test_*.py', '-v'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'analysis_tools', '-p', 'test_*.py', '-v'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'experiment_tools', '-p', 'test_*.py', '-v'],
        ['node', '--check', 'dist/app.js'],
        ['node', '--test', *[str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests').glob('test_web*.mjs'))]],
    ]
    for command in commands:
        print('\n==> ' + ' '.join(command), flush=True)
        try:
            result = subprocess.run(command, cwd=ROOT, timeout=300, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f'Check could not finish: {exc}', file=sys.stderr)
            return 1
        if result.returncode:
            return result.returncode if result.returncode > 0 else 1
    print('\nOffline tooling checks passed. No models executed; full Java fixture suite is separate.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

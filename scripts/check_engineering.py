"""Runs checked-in trusted fixture selfchecks, never model submissions.

Not a secure sandbox. The outer runner's timeout/resource policy still applies.

With no arguments, or with --all, every tier run_all.py plus S04-spring runs.
--m1 runs only the M1 four-gate checks for B02, S01, S04, S04-spring, G01, and G05
and exits non-zero unless every required gate passes. --m1 is not used by check_fast.py.
"""
from pathlib import Path
import argparse, os, signal, subprocess, sys, tempfile, time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import m1_gates


def run_full_suite():
    for tier in ('bronze', 'silver', 'gold', 'diamond', 'king'):
        runner = ROOT / 'engineering' / tier / 'run_all.py'
        if not runner.exists():
            print(f'{tier}: suite not implemented; skipped (not a pass)', flush=True)
            continue
        print(f'=== {tier} ===', flush=True)
        with tempfile.TemporaryFile() as out:
            proc = subprocess.Popen([sys.executable, '-B', str(runner)], cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 600
            while proc.poll() is None:
                if time.monotonic() > deadline or os.fstat(out.fileno()).st_size > 4 * 1024 * 1024:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    raise SystemExit(f'{tier}: time/output limit')
                time.sleep(.2)
            out.seek(0)
            print(out.read(4 * 1024 * 1024).decode(errors='replace'))
            if proc.returncode:
                raise SystemExit(f'{tier}: failed ({proc.returncode})')
    spring = ROOT / 'engineering/integration/S04-spring/run_selfcheck.py'
    if spring.exists():
        print('=== S04-spring integration ===', flush=True)
        result = subprocess.run([sys.executable, '-B', str(spring)], cwd=ROOT, timeout=240)
        if result.returncode:
            raise SystemExit('S04-spring failed')
    return 0


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--m1', action='store_true', help='Run four-gate checks for B02, S01, S04, S04-spring, G01, and G05 only')
    parser.add_argument('--all', action='store_true', help='Run every tier selfcheck suite (also the default)')
    return parser.parse_args(argv)


def main(argv=None, *, gates_impl=None, full_impl=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    if args.m1 and args.all:
        print('Pass only one of --m1 or --all.', file=sys.stderr)
        return 2
    if args.m1:
        return (gates_impl or m1_gates.run)()
    return (full_impl or run_full_suite)()


if __name__ == '__main__':
    sys.exit(main())

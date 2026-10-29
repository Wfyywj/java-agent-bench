#!/usr/bin/env python3
"""Directed counterexample: stale gates_green must not survive a bound source change.

Audit F3 / TRUSTWORTHY_EXPERIMENTS A2. Does not run Java or M1. Copies the
checkout, applies bound-source.patch, and rebuilds the implementation catalog
in that copy. Exit 0 when the defense holds (verdict: blocks). Exit 1 when
B02 stays gates_green (verdict: still-fails) or the repro cannot run.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in [HERE, *HERE.parents] if (p / 'scripts' / 'build_implementations.py').is_file())
PATCH = HERE / 'bound-source.patch'
SENTINEL = 'directed-counterexample: bound source byte after gates_green evidence (F3)'


def repo_root():
    return ROOT


def ignore_copy(directory, names):
    skip = {'.git', '__pycache__', 'node_modules', 'target', '.deps', '.local', 'agent-workspaces', 'private-evaluators'}
    return [name for name in names if name in skip or name.endswith('.pyc')]


def apply_patch(copy):
    """Apply the checked-in unified diff. Pure Python so a clean clone needs no patch(1)."""
    target = None
    added = []
    for line in PATCH.read_text(encoding='utf-8').splitlines():
        if line.startswith('+++ '):
            path = line[4:]
            if path.startswith('b/'):
                path = path[2:]
            target = copy / path
        elif line.startswith('+') and not line.startswith('+++'):
            added.append(line[1:])
    if target is None or added != [SENTINEL]:
        raise SystemExit('bound-source.patch is not the expected one-line append')
    original = target.read_text(encoding='utf-8')
    if SENTINEL in original:
        raise SystemExit('sentinel already present; refusing to double-apply')
    if not original.endswith('\n'):
        original += '\n'
    target.write_text(original + SENTINEL + '\n', encoding='utf-8')
    return target.relative_to(copy)


def load_impl(path):
    return json.loads(path.read_text(encoding='utf-8'))


def b02_record(records):
    return next(record for record in records if record.get('implementation_id') == 'B02-slice')


def green_ids(records):
    return sorted(record['implementation_id'] for record in records if record.get('status') == 'gates_green')


def main():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import m1_gates as gates

    catalog = ROOT / 'catalog' / 'implementations.json'
    tasks_path = ROOT / 'catalog' / 'tasks.json'
    evidence = ROOT / 'engineering' / 'bronze' / 'B02' / 'evidence' / 'm1-four-gates.json'
    before_catalog = catalog.read_bytes()
    before_tasks = tasks_path.read_bytes()
    before_evidence = evidence.read_bytes()
    copy_dir = Path(tempfile.mkdtemp(prefix='stale-gates-green-'))
    try:
        shutil.copytree(ROOT, copy_dir, ignore=ignore_copy, dirs_exist_ok=True)
        copy_evidence = copy_dir / 'engineering' / 'bronze' / 'B02' / 'evidence' / 'm1-four-gates.json'
        evidence_bytes = copy_evidence.read_bytes()
        evidence_doc = json.loads(evidence_bytes)
        before_fp = gates.source_fingerprint(copy_dir, 'B02')
        if before_fp['sha256'] != evidence_doc['evidence_fingerprint']['sha256']:
            print('verdict: still-fails')
            print('precondition: checked-in B02 evidence is not bound to this tree')
            print('fingerprint_now=' + before_fp['sha256'])
            print('fingerprint_evidence=' + evidence_doc['evidence_fingerprint']['sha256'])
            return 1
        checked_in = b02_record(load_impl(copy_dir / 'catalog' / 'implementations.json'))
        if checked_in.get('status') != 'gates_green':
            print('verdict: still-fails')
            print('precondition: checked-in B02-slice is not gates_green')
            return 1
        greens_before = green_ids(load_impl(copy_dir / 'catalog' / 'implementations.json'))
        mutated = apply_patch(copy_dir)
        after_fp = gates.source_fingerprint(copy_dir, 'B02')
        if after_fp['sha256'] == before_fp['sha256']:
            print('verdict: still-fails')
            print('patch did not change the B02 source fingerprint')
            return 1
        build = subprocess.run(
            [sys.executable, 'scripts/build_implementations.py'],
            cwd=copy_dir, capture_output=True, text=True, timeout=120,
        )
        records = load_impl(copy_dir / 'catalog' / 'implementations.json')
        record = b02_record(records)
        tasks = json.loads((copy_dir / 'catalog' / 'tasks.json').read_text(encoding='utf-8'))
        b02_task = next(task for task in tasks if task.get('id') == 'B02')
        greens_after = green_ids(records)
        evidence_unchanged = copy_evidence.read_bytes() == evidence_bytes
        stayed_green = record.get('status') == 'gates_green'
        others_kept = set(greens_before) - {'B02-slice'} <= set(greens_after)
        blocked = (
            build.returncode == 0
            and not stayed_green
            and record.get('gate_status') == 'stale'
            and 'slice_implementation' not in b02_task
            and evidence_unchanged
            and evidence_doc.get('pass') is True
            and others_kept
            and all(key not in record for key in ('full_catalog_ready', 'slice_kind', 'gates_evidence'))
        )
        print('class: stale-gates-green')
        print('audit: F3 historical gates_green; TRUSTWORTHY_EXPERIMENTS A2')
        print('mutated: ' + mutated.as_posix())
        print('fingerprint_before: ' + before_fp['sha256'])
        print('fingerprint_after: ' + after_fp['sha256'])
        print('build_exit: ' + str(build.returncode))
        print('build_stdout: ' + build.stdout.strip())
        if build.stderr.strip():
            print('build_stderr: ' + build.stderr.strip())
        print(
            'B02-slice: status={status} gate_status={gate}'.format(
                status=record.get('status'), gate=record.get('gate_status'),
            )
        )
        print('B02_slice_implementation: ' + ('present' if 'slice_implementation' in b02_task else 'absent'))
        print('historical_evidence_pass: ' + str(bool(evidence_doc.get('pass'))))
        print('evidence_bytes_unchanged: ' + str(evidence_unchanged))
        print('gates_green_before: ' + ','.join(greens_before))
        print('gates_green_after: ' + ','.join(greens_after))
        print('verdict: ' + ('blocks' if blocked else 'still-fails'))
        if not blocked and not stayed_green:
            print('defense did not leave B02 green, but a required stale-catalog assertion failed')
        return 0 if blocked else 1
    finally:
        shutil.rmtree(copy_dir, ignore_errors=True)
        if catalog.read_bytes() != before_catalog or tasks_path.read_bytes() != before_tasks or evidence.read_bytes() != before_evidence:
            print('checkout catalog or B02 evidence changed; repro must stay disposable', file=sys.stderr)
            return 1


if __name__ == '__main__':
    sys.exit(main())

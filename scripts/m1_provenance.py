"""Content binding and atomic, append-only M1 attempt storage (not signatures)."""
from pathlib import Path
import hashlib
import json
import os

ALGORITHM = 'sha256-source-bundle/v1'
# Only known generated outputs are omitted. Evidence inputs (seed/schema/logs)
# remain bound. Adding/deleting/renaming any other task file changes the digest.
OUTPUT_NAMES = {'m1-four-gates.json', 'verification-results.json', 'selfcheck.json',
                'selfcheck-run2.json', 'audit-repeatability.json'}
IGNORED_DIRS = {'__pycache__', '.git', '.deps', 'target', 'build', '.build'}


def source_fingerprint(root, task_rel):
    root = Path(root).resolve()
    folder = root / task_rel
    if not (folder / 'task.json').is_file():
        raise ValueError('missing task manifest: ' + task_rel)
    paths = set()
    for base in (folder, root / 'scripts', root / 'engineering_tools', root / 'harness', root / 'schemas'):
        if base.exists():
            paths.update(p for p in base.rglob('*') if p.is_file() or p.is_symlink())
    # Shared verifier, bootstrap and orchestration inputs outside the task.
    for tier in ('bronze', 'silver', 'gold', 'diamond', 'king'):
        paths.update((root / 'engineering' / tier).glob('*.py'))
    for name in ('pyproject.toml', 'requirements.txt', 'requirements.lock', 'pom.xml'):
        if (root / name).is_file():
            paths.add(root / name)
    rows = []
    for path in sorted(paths):
        rel = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in rel.parts) or path.suffix in ('.pyc', '.class'):
            continue
        if path.name in OUTPUT_NAMES:
            continue
        if path.is_symlink():
            raise ValueError('source bundle contains symlink: ' + rel.as_posix())
        rows.append({'path': rel.as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'algorithm': ALGORITHM, 'sha256': digest, 'files': rows}


def atomic_json(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with tmp.open('w') as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

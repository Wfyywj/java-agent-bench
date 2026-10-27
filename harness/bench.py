#!/usr/bin/env python3
"""Offline functional Java evaluation, deliberately NOT a security sandbox."""
import argparse
import datetime
import difflib
import hashlib
import json
import os
import math
import selectors
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / 'tasks'
ID = re.compile(r'R[0-9]{2}')
CHECK = re.compile(r'^(PASS|FAIL) ([A-Za-z0-9_.-]+)(?: (.*))?$')


def confined(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('absolute paths and parent traversal forbidden')
    result = root / rel
    if result.is_symlink() or not result.resolve().is_relative_to(root):
        raise ValueError('symlink/path escape forbidden')
    return result


def source_files(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('source root must be a real directory')
    files = []
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('symlinks forbidden in source trees')
        if path.is_file() and path.suffix == '.java':
            confined(root, path.relative_to(root))
            files.append(path)
    if not files:
        raise ValueError('no Java sources found')
    return files


def task(task_id):
    if not ID.fullmatch(task_id):
        raise ValueError('task id must match R plus two digits')
    directory = confined(TASKS, task_id)
    manifest = json.loads((directory / 'task.json').read_text())
    if manifest['id'] != task_id or not isinstance(manifest['version'], str):
        raise ValueError('invalid task identity/version')
    if not isinstance(manifest['test_count'], int) or manifest['test_count'] < 8:
        raise ValueError('tasks require at least eight checks')
    if len(manifest['check_names']) != manifest['test_count'] or len(set(manifest['check_names'])) != manifest['test_count']:
        raise ValueError('check names must be unique and match test count')
    for name in ['candidate/src', 'reference/src', 'verifier']:
        source_files(confined(directory, name))
    if not (directory / 'PROMPT.md').is_file():
        raise ValueError('missing task prompt')
    return directory, manifest


def copy_java(source, destination):
    for path in source_files(source):
        target = confined(destination, path.relative_to(source))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def prepare(task_id, destination):
    directory, manifest = task(task_id)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('destination must not exist (never overwrites work)')
    destination.mkdir(parents=True)
    copy_java(directory / 'candidate/src', destination / 'src')
    shutil.copyfile(directory / 'PROMPT.md', destination / 'PROMPT.md')
    (destination / 'task.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return {'task_id': task_id, 'workspace': str(destination.resolve()),
            'copied': ['src/*.java (recursive)', 'PROMPT.md', 'task.json'],
            'security_note': 'Sanitized copy only; local repository tests/reference remain public.'}


def command(argv, cwd, timeout, output_limit=1048576):
    if not math.isfinite(timeout) or timeout <= 0 or output_limit < 1:
        raise ValueError('positive finite timeout and output limit required')
    start = time.monotonic()
    proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    expired = limited = False
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    size = 0
    def kill():
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    with selectors.DefaultSelector() as selector:
        for name, pipe in [('stdout', proc.stdout), ('stderr', proc.stderr)]:
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, name)
        try:
            while selector.get_map():
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    expired = True
                    kill()
                    break
                for key, _ in selector.select(min(remaining, .1)):
                    data = os.read(key.fileobj.fileno(), 8192)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    room = output_limit - size
                    buffers[key.data].extend(data[:room])
                    size += min(room, len(data))
                    if len(data) > room:
                        limited = True
                        kill()
                        break
                if limited:
                    break
            if not (expired or limited):
                try:
                    proc.wait(timeout=max(.001, timeout - (time.monotonic() - start)))
                except subprocess.TimeoutExpired:
                    expired = True
                    kill()
        finally:
            proc.stdout.close()
            proc.stderr.close()
            if proc.poll() is None:
                kill()
            proc.wait()
    return {'argv': argv, 'exit_code': proc.returncode, 'timed_out': expired,
            'output_limited': limited, 'output_limit_bytes': output_limit,
            'duration_seconds': round(time.monotonic() - start, 4),
            'stdout': buffers['stdout'].decode('utf-8', errors='replace'),
            'stderr': buffers['stderr'].decode('utf-8', errors='replace')}


def tree_text(root):
    return {str(p.relative_to(root)): p.read_text() for p in source_files(root)}


def patch_hash(baseline, candidate):
    before, after = tree_text(baseline), tree_text(candidate)
    patch = []
    for name in sorted(before.keys() | after.keys()):
        patch.extend(difflib.unified_diff(before.get(name, '').splitlines(keepends=True),
                     after.get(name, '').splitlines(keepends=True), fromfile='a/' + name,
                     tofile='b/' + name))
    return hashlib.sha256(''.join(patch).encode()).hexdigest()


def evaluate(task_id, candidate, timeout=20):
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 300:
        raise ValueError('timeout must be greater than zero and at most 300 seconds')
    directory, manifest = task(task_id)
    candidate = Path(candidate)
    source_files(candidate)
    java = shutil.which('java')
    if not java:
        raise ValueError('Java 21+ runtime with jdk.compiler module required')
    version = command([java, '-version'], ROOT, 5)
    result = {'schema_version': '1.0', 'task_id': task_id,
              'task_version': manifest['version'],
              'category': manifest['category'], 'tier': manifest['tier'],
              'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'patch_sha256': patch_hash(directory / 'candidate/src', candidate),
              'environment': {'java': version['stderr'].strip() or version['stdout'].strip(),
                              'python': platform.python_version(), 'platform': platform.platform()},
              'expected_checks': manifest['test_count'], 'checks': [], 'passed': False,
              'status': 'build_failed', 'security': 'local functional evaluation; not a security sandbox'}
    with tempfile.TemporaryDirectory(prefix='java-bench-') as tmp:
        build = Path(tmp)
        copy_java(candidate, build / 'candidate')
        copy_java(directory / 'verifier', build / 'verifier')
        (build / 'classes').mkdir()
        sources = sorted(str(p.relative_to(build)) for p in build.rglob('*.java'))
        compile_result = command([java, '-m', 'jdk.compiler/com.sun.tools.javac.Main',
                                  '-encoding', 'UTF-8', '-proc:none', '-d', 'classes', *sources], build, timeout)
        result['compile'] = compile_result
        result['run'] = None
        if compile_result['output_limited']:
            result['status'] = 'compile_output_limit'
        elif compile_result['timed_out']:
            result['status'] = 'compile_timeout'
        elif compile_result['exit_code'] == 0:
            run = command([java, '-Xmx256m', '-cp', 'classes', 'Verifier'], build, timeout)
            result['run'] = run
            for line in run['stdout'].splitlines():
                match = CHECK.fullmatch(line)
                if match:
                    result['checks'].append({'name': match[2], 'passed': match[1] == 'PASS',
                                             'detail': match[3] or ''})
            names = [c['name'] for c in result['checks']]
            complete = len(names) == manifest['test_count'] and set(names) == set(manifest['check_names'])
            result['passed'] = (not run['timed_out'] and not run['output_limited'] and run['exit_code'] == 0 and complete
                                and all(c['passed'] for c in result['checks']))
            result['status'] = ('run_output_limit' if run['output_limited'] else 'run_timeout' if run['timed_out'] else 'passed' if result['passed']
                                else 'verification_failed')
    return result


def selfcheck(task_id, timeout=20):
    directory, manifest = task(task_id)
    baseline = evaluate(task_id, directory / 'candidate/src', timeout)
    reference = evaluate(task_id, directory / 'reference/src', timeout)
    definitions = json.loads((directory / 'mutations.json').read_text())
    mutations = []
    for definition in definitions:
        with tempfile.TemporaryDirectory(prefix='java-mutant-') as tmp:
            src = Path(tmp) / 'src'
            copy_java(directory / 'reference/src', src)
            target = confined(src, definition['file'])
            text = target.read_text()
            if text.count(definition['old']) != 1:
                raise ValueError('mutation must match exactly once')
            target.write_text(text.replace(definition['old'], definition['new']))
            mutant = evaluate(task_id, src, timeout)
        killed = mutant['status'] == 'verification_failed' and any(not c['passed'] for c in mutant['checks'])
        mutations.append({'reason': definition['reason'], 'result': mutant, 'killed': killed})
    success = (baseline['status'] == 'verification_failed' and
               any(not c['passed'] for c in baseline['checks']) and reference['passed']
               and bool(mutations) and all(m['killed'] for m in mutations))
    return {'task_id': task_id, 'passed': success, 'baseline': baseline, 'reference': reference,
            'mutation': mutations[0]['result'], 'mutation_reason': mutations[0]['reason'],
            'mutation_killed': all(m['killed'] for m in mutations), 'mutations': mutations}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('validate-task', 'prepare', 'evaluate', 'selfcheck'):
        p = sub.add_parser(action)
        p.add_argument('task_id')
        if action == 'prepare':
            p.add_argument('destination')
        if action == 'evaluate':
            p.add_argument('candidate', help='directory containing candidate Java source files')
        if action in ('evaluate', 'selfcheck'):
            p.add_argument('--timeout', type=float, default=20, help='seconds per compilation/execution phase')
        p.add_argument('--output', help='also write JSON result to this file')
    args = parser.parse_args(argv)
    try:
        if args.action == 'validate-task':
            _, manifest = task(args.task_id)
            result = {'valid': True, 'manifest': manifest}
        elif args.action == 'prepare':
            result = prepare(args.task_id, args.destination)
        elif args.action == 'evaluate':
            result = evaluate(args.task_id, args.candidate, args.timeout)
        else:
            result = selfcheck(args.task_id, args.timeout)
        payload = json.dumps(result, indent=2) + '\n'
        if args.output:
            Path(args.output).write_text(payload)
        print(payload, end='')
        return 0 if result.get('passed', True) else 1
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())

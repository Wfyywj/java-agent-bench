"""M1 four-gate evidence for the locked task list.

Trusted fixture selfchecks only. This is not a secure sandbox and it never
runs model submissions. Baseline is recorded as baseline: these tasks have
no separate nop fixture.
"""
from pathlib import Path
import hashlib, json, os, re, signal, subprocess, sys, time, uuid
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m1_provenance import source_fingerprint as _source_fingerprint, atomic_json

def source_fingerprint(root, task_id):
    return _source_fingerprint(root, TASK_DIRS[task_id])

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'm1-four-gates/v1'
SUMMARY_SCHEMA = 'm1-four-gates-summary/v1'
GATE_NAMES = ('reference', 'nop_or_baseline', 'mutants', 'repeat')
M1_TASK_IDS = ('B02', 'S01', 'S04', 'S04-spring', 'G01', 'G05')
TASK_DIRS = {
    'B02': 'engineering/bronze/B02',
    'S01': 'engineering/silver/S01',
    'S04': 'engineering/silver/S04',
    'S04-spring': 'engineering/integration/S04-spring',
    'G01': 'engineering/gold/G01',
    'G05': 'engineering/gold/G05',
}
SCRIPTS = {
    'B02': ('run_selfcheck.py', ()),
    'S01': ('run_selfcheck.py', ()),
    'S04': ('run_selfcheck.py', ()),
    'S04-spring': ('run_selfcheck.py', ()),
    'G01': ('selfcheck.py', ()),
    'G05': ('selfcheck.py', ('--write-evidence',)),
}
INVOCATIONS = {'B02': 2}
TIMEOUTS = {'B02': 180, 'S01': 300, 'S04': 300, 'S04-spring': 600, 'G01': 300, 'G05': 420}
REPORT_FILES = {
    'S01': 'evidence/selfcheck.json',
    'S04': 'evidence/selfcheck.json',
    'S04-spring': 'evidence/selfcheck.json',
    'G01': 'verification-results.json',
    'G05': 'verification-results.json',
}
# Public verifier names that exercise a critical acceptance criterion.
# B02/S01/S04 carry acceptance ids on the checks themselves.
EXPLICIT_CRITICAL = {
    'G01': frozenset({
        'same request replay one hold',
        'key bound to tenant',
        'key bound to lease',
        'failed commit records pending compensation',
        'restart recovery durably releases',
        'compensation survives second restart',
    }),
    'G05': frozenset({'I01', 'I02', 'I07'}),
    'S04-spring': frozenset({
        'active-transaction-at-repository',
        'successful-cancel-atomic-state',
        'checked-mid-batch-rollback',
        'runtime-mid-batch-rollback',
        'late-checked-failure-rollback',
        'mixed-cancelled-pending-failure-rolls-back',
    }),
}
WARNING = (
    'NOT a secure sandbox. M1 gates run checked-in trusted fixtures only; '
    'model submissions are not executed.'
)


def task_dir(root, task_id):
    return Path(root) / TASK_DIRS[task_id]


def evidence_rel(task_id):
    return f'{TASK_DIRS[task_id]}/evidence/m1-four-gates.json'


def invocation_plan(root, task_id):
    folder = task_dir(root, task_id)
    script, extra = SCRIPTS[task_id]
    argv = [sys.executable, '-B', str(folder / script), *extra]
    timeout = TIMEOUTS[task_id]
    return [(argv, timeout) for _ in range(INVOCATIONS.get(task_id, 1))]


def _acceptance_ids(manifest):
    found = set()
    groups = []
    for key in ('original_acceptance', 'acceptance'):
        if isinstance(manifest.get(key), list):
            groups.append(manifest[key])
    scope = manifest.get('original_scope') or {}
    if isinstance(scope.get('acceptance'), list):
        groups.append(scope['acceptance'])
    for group in groups:
        for item in group:
            if isinstance(item, dict) and item.get('critical') is True and isinstance(item.get('id'), str):
                found.add(item['id'])
    return found


def _is_critical(task_id, label, manifest):
    explicit = EXPLICIT_CRITICAL.get(task_id)
    if explicit is not None:
        return any(label == item or label.startswith(item + ' ') for item in explicit)
    ids = set(re.findall(r'[BSGDK]\d{2}-A\d{2}', label))
    return bool(ids & _acceptance_ids(manifest))


def _clean_label(body):
    body = body.strip()
    for marker in (' java.lang.', ' AssertionError:', ' Exception in'):
        idx = body.find(marker)
        if idx != -1:
            body = body[:idx]
    return body.strip()


def _status_checks(output, task_id, manifest):
    checks = []
    for line in (output or '').splitlines():
        assertion_failure = line.startswith('FAIL ')
        if line.startswith('ERROR '):
            name, passed = _clean_label(line[6:]), False
        elif line.startswith('PASS '):
            name, passed = _clean_label(line[5:]), True
        elif line.startswith('FAIL '):
            name, passed = _clean_label(line[5:]), False
        else:
            continue
        if name:
            checks.append({'name': name, 'passed': passed, 'critical': _is_critical(task_id, name, manifest), 'assertion_failure': assertion_failure, 'infrastructure_error': line.startswith('ERROR ')})
    return checks


def _check_hash(checks):
    rows = sorted((c['name'], bool(c['passed']), c.get('acceptance')) for c in checks)
    payload = json.dumps(rows, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _unique(items):
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _load_manifest(root, task_id):
    return json.loads((task_dir(root, task_id) / 'task.json').read_text())


def mutants_of(root, task_id):
    if task_id not in TASK_DIRS:
        return None
    path = task_dir(root, task_id) / 'task.json'
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text())
        mutants = document.get('mutants') if isinstance(document, dict) else None
    except (OSError, ValueError):
        return None
    return mutants if isinstance(mutants, list) else None


def _b02_checks(variant, manifest):
    checks = []
    for name in sorted((variant.get('checks') or {})):
        value = variant['checks'][name]
        checks.append({
            'name': name,
            'passed': value == 'PASS',
            'assertion_failure': isinstance(value, str) and value.startswith('FAIL'),
            'critical': _is_critical('B02', name, manifest),
        })
    return checks


def _b02_passed(variant, checks):
    return bool(variant.get('passed')) and bool(checks) and all(c['passed'] for c in checks)


def _normalize_b02(manifest, reports):
    reference, baseline, mutants = [], [], {mid: [] for mid in manifest['mutants']}
    for report in reports:
        variants = report.get('variants') or {}
        if 'reference' not in variants or 'baseline' not in variants:
            raise ValueError('B02 report is missing reference or baseline')
        ref_checks = _b02_checks(variants['reference'], manifest)
        reference.append({'passed': _b02_passed(variants['reference'], ref_checks), 'checks': ref_checks})
        base_checks = _b02_checks(variants['baseline'], manifest)
        baseline.append({
            'passed': _b02_passed(variants['baseline'], base_checks),
            'checks': base_checks,
            'runnable': bool(base_checks),
            'reason': None if base_checks else 'baseline produced no checks',
        })
        for mid in manifest['mutants']:
            mutants[mid].append(_mutant_from_b02(variants.get(mid), manifest))
    return {'reference_runs': reference, 'baseline_runs': baseline, 'mutants': mutants}


def _mutant_from_b02(variant, manifest):
    if not isinstance(variant, dict):
        return {'runnable': False, 'failed': None, 'reason': 'not present in selfcheck report'}
    checks = _b02_checks(variant, manifest)
    if not checks:
        return {'runnable': False, 'failed': None, 'reason': 'mutant produced no checks'}
    if any(v != 'PASS' and not (isinstance(v, str) and v.startswith('FAIL:')) for v in variant.get('checks', {}).values()):
        return _nonsemantic('infrastructure_error', 'verifier reported non-assertion error')
    passed = _b02_passed(variant, checks)
    if not passed and not any(c.get('assertion_failure') for c in checks):
        return _nonsemantic('infrastructure_error', 'no explicit assertion failure')
    if passed:
        return {'runnable': True, 'failed': False, 'reason': 'mutant passed the verifier'}
    return {'runnable': True, 'failed': True, 'reason': None, 'failed_assertions': [c['name'] for c in checks if c.get('assertion_failure')]}


def _comparison_failed(comparison):
    if not isinstance(comparison, dict) or comparison.get('passed') is not False or comparison.get('error'):
        return False
    if 'actual' not in comparison or 'expected' not in comparison:
        return False
    actual, expected = comparison['actual'], comparison['expected']
    return actual not in expected if isinstance(expected, list) else actual != expected


def _silver_assertion_failure(check):
    steps = check.get('steps') or []
    if check.get('passed') is not False or check.get('error') or not steps:
        return False
    for step in steps:
        if not isinstance(step, dict) or step.get('error') or 'actual' not in step or 'expected' not in step:
            return False
        probe = step.get('jdbc_probe')
        if probe is not None and (not isinstance(probe, dict) or probe.get('error') or 'actual' not in probe or 'expected' not in probe):
            return False
    return any(step.get('passed') is False and (_comparison_failed(step) or _comparison_failed(step.get('jdbc_probe'))) for step in steps)


def _silver_run(run, manifest, task_id):
    checks = []
    for item in run.get('checks') or []:
        name = str(item.get('name') or '')
        acceptance = item.get('acceptance')
        label = f'{name} {acceptance or ""}'.strip()
        checks.append({
            'name': name,
            'passed': item.get('passed') is True,
            'critical': _is_critical(task_id, label, manifest),
            'acceptance': acceptance if isinstance(acceptance, str) else None,
            'assertion_failure': _silver_assertion_failure(item),
            'infrastructure_error': bool(item.get('error') or any(step.get('error') for step in item.get('steps', []))),
        })
    passed = bool(checks) and run.get('passed') == run.get('total') == len(checks) and all(c['passed'] for c in checks)
    return {'passed': passed, 'checks': checks}


def _normalize_silver(task_id, manifest, report):
    variants = report.get('variants') or {}
    if 'reference' not in variants or 'baseline' not in variants:
        raise ValueError(f'{task_id} selfcheck is missing reference or baseline')
    reference = [_silver_run(run, manifest, task_id) for run in variants['reference'].get('runs') or []]
    if not variants['reference'].get('compiled'):
        reference = [{'passed': False, 'checks': [], 'reason': variants['reference'].get('error') or 'reference did not compile'}]
    baseline = _baseline_from_silver(variants['baseline'], manifest, task_id)
    mutants = {}
    for mid in manifest['mutants']:
        mutants[mid] = [_mutant_from_silver(variants.get(mid))]
    return {'reference_runs': reference, 'baseline_runs': baseline, 'mutants': mutants}


def _baseline_from_silver(item, manifest, task_id):
    if not isinstance(item, dict) or not item.get('compiled'):
        reason = (item or {}).get('error') or 'baseline did not compile'
        return [{'passed': False, 'checks': [], 'runnable': False, 'reason': reason}]
    runs = [_silver_run(run, manifest, task_id) for run in item.get('runs') or []]
    if not runs:
        return [{'passed': False, 'checks': [], 'runnable': False, 'reason': 'baseline produced no runs'}]
    for run in runs:
        run['runnable'] = bool(run['checks']) and not any(c.get('infrastructure_error') for c in run['checks'])
        run['reason'] = None if run['runnable'] else 'baseline infrastructure error'
    return runs


def _silver_run_passed(run):
    checks = run.get('checks') or []
    return bool(checks) and run.get('passed') == run.get('total') == len(checks) and all(item.get('passed') is True for item in checks)


def _silver_run_failed(run):
    checks = run.get('checks') or []
    if not checks:
        return False
    return any(_silver_assertion_failure(item) for item in checks)


def _mutant_from_silver(item):
    if not isinstance(item, dict):
        return {'runnable': False, 'failed': None, 'reason': 'not present in selfcheck report'}
    if not item.get('compiled'):
        return {'runnable': False, 'failed': None, 'reason': item.get('error') or 'mutant did not compile'}
    runs = item.get('runs') or []
    if any(c.get('error') or any(step.get('error') for step in c.get('steps', [])) for run in runs for c in run.get('checks', [])):
        reason = str([c for run in runs for c in run.get('checks', []) if c.get('error') or any(step.get('error') for step in c.get('steps', []))])
        return _nonsemantic('timeout' if 'timeout' in reason.lower() else 'infrastructure_error', reason)
    if not runs or any(not run.get('checks') for run in runs):
        return {'runnable': False, 'failed': None, 'reason': 'mutant produced no runs'}
    if any(c.get('passed') is False and not _silver_assertion_failure(c) for run in runs for c in run.get('checks', [])):
        return _nonsemantic('missing_report', 'failed silver check lacks completed mismatching comparison evidence')
    if all(_silver_run_passed(run) for run in runs):
        return {'runnable': True, 'failed': False, 'reason': 'mutant passed the verifier'}
    if all(_silver_run_failed(run) for run in runs):
        return {'runnable': True, 'failed': True, 'reason': None, 'failed_assertions': _unique([c['name'] for run in runs for c in run['checks'] if _silver_assertion_failure(c)])}
    return {'runnable': True, 'failed': False, 'reason': 'mutant did not fail every run'}


def _normalize_spring(manifest, report):
    reference_raw = report.get('reference')
    baseline_raw = report.get('baseline')
    if not isinstance(reference_raw, list) or not isinstance(baseline_raw, dict):
        raise ValueError('S04-spring report is missing reference runs or baseline')
    reference = [_spring_reference(item, manifest) for item in reference_raw]
    baseline = [_spring_baseline(baseline_raw, manifest)]
    mutant_raw = report.get('mutants') or {}
    mutants = {mid: [_spring_mutant(mutant_raw.get(mid))] for mid in manifest['mutants']}
    return {'reference_runs': reference, 'baseline_runs': baseline, 'mutants': mutants}


def _spring_compile_ok(item):
    return isinstance(item, dict) and (item.get('compile') or {}).get('exit') == 0


def _spring_reference(item, manifest):
    checks = _status_checks((item.get('test') or {}).get('output'), 'S04-spring', manifest) if isinstance(item, dict) else []
    passed = _spring_compile_ok(item) and (item.get('test') or {}).get('exit') == 0 and _completed_output((item.get('test') or {}).get('output'), 'S04-spring') and item.get('passed') is True and bool(checks) and all(c['passed'] for c in checks)
    return {'passed': passed, 'checks': checks}


def _spring_baseline(item, manifest):
    if not _spring_compile_ok(item) or not _completed_output((item.get('test') or {}).get('output'), 'S04-spring'):
        return {'passed': False, 'checks': [], 'runnable': False, 'reason': 'baseline did not compile'}
    checks = _status_checks((item.get('test') or {}).get('output'), 'S04-spring', manifest)
    passed = item.get('passed') is True and bool(checks) and all(c['passed'] for c in checks)
    runnable = not any(c.get('infrastructure_error') for c in checks)
    return {'passed': passed, 'checks': checks, 'runnable': runnable, 'reason': None if runnable else 'baseline infrastructure error'}


def _nonsemantic(outcome, reason):
    return {'runnable': False, 'failed': None, 'reason': reason, 'outcome': outcome, 'failed_assertions': []}


def _completed_output(output, task_id):
    lines = (output or '').splitlines()
    statuses = [line.split(' ', 1)[0] for line in lines if line.startswith(('PASS ', 'FAIL ', 'ERROR '))]
    patterns = {'G01': r'INVARIANTS=(\d+) FAILURES=(\d+)',
                'G05': r'SUMMARY passed=(\d+) failed=(\d+)',
                'S04-spring': r'RESULT tests=(\d+) failed=(\d+)'}
    matches = [re.fullmatch(patterns[task_id], line) for line in lines]
    matches = [m for m in matches if m]
    names = [_clean_label(line.split(' ', 1)[1]) for line in lines if line.startswith(('PASS ', 'FAIL ', 'ERROR '))]
    if len(set(names)) != len(names):
        return False
    if len(matches) != 1 or not statuses:
        return False
    first, failures = map(int, matches[0].groups())
    total = first + failures if task_id == 'G05' else first
    return total == len(statuses) and failures == sum(s != 'PASS' for s in statuses)


def _spring_mutant(item):
    if not isinstance(item, dict):
        return _nonsemantic('missing_report', 'not present in selfcheck report')
    if not _spring_compile_ok(item):
        return _nonsemantic('compile_error', 'mutant did not compile')
    test = item.get('test') or {}
    if test.get('timeout') or test.get('exit') == 124:
        return _nonsemantic('timeout', 'mutant timed out')
    if test.get('exit') not in (0, 1):
        return _nonsemantic('startup_error', 'mutant did not complete verifier')
    if (test.get('exit') == 0) != (item.get('passed') is True):
        return _nonsemantic('infrastructure_error', 'inconsistent verifier exit and pass flag')
    checks = _status_checks(test.get('output'), 'S04-spring', {})
    if any(c.get('infrastructure_error') for c in checks):
        return _nonsemantic('infrastructure_error', 'verifier reported non-assertion error')
    if not checks or not _completed_output(test.get('output'), 'S04-spring'):
        return _nonsemantic('missing_report', 'mutant produced no complete report')
    return _grouped_mutant({'ran': True, 'passed': item.get('passed') is True, 'reason': None}, checks)


def _row_checks(row, task_id, manifest):
    return _status_checks(row.get('output'), task_id, manifest)


def _normalize_g01(manifest, report):
    return _normalize_grouped(manifest, report, 'G01', _g01_state)


def _normalize_g05(manifest, report):
    return _normalize_grouped(manifest, report, 'G05', _g05_state)


def _g01_state(row):
    if row.get('exit') == 124:
        return {'ran': False, 'passed': False, 'reason': 'mutant timed out', 'outcome': 'timeout'}
    ran = row.get('phase') == 'verify' and row.get('exit') in (0, 1) and (row.get('passed') is True) == (row.get('exit') == 0) and _completed_output(row.get('output'), 'G01')
    if not ran:
        reason = 'compile failure is not a killed mutant' if row.get('phase') == 'compile' else 'variant did not reach verify'
        return {'ran': False, 'passed': False, 'reason': reason}
    checks = None
    passed = row.get('passed') is True and row.get('exit') == 0
    return {'ran': True, 'passed': passed, 'reason': None}


def _g05_state(row):
    incident = row.get('incident') or {}
    if row.get('exit_code') == 124 or incident.get('exit_code') == 124:
        return {'ran': False, 'passed': False, 'reason': 'mutant timed out', 'outcome': 'timeout'}
    ran = row.get('stage') == 'verify' and row.get('exit_code') in (0, 1) and row.get('failure') is None and incident.get('exit_code') == 0 and 'exit_code' in row and _completed_output(row.get('output'), 'G05')
    if not ran:
        reason = row.get('failure') or ('compile failure is not a killed mutant' if row.get('stage') == 'compile' else 'variant did not reach verify')
        return {'ran': False, 'passed': False, 'reason': str(reason)}
    passed = row.get('exit_code') == 0
    return {'ran': True, 'passed': passed, 'reason': None}


def _variant_key(task_id, name):
    if task_id == 'G05' and isinstance(name, str) and name.startswith('mutants/'):
        return name.split('/', 1)[1]
    return name


def _normalize_grouped(manifest, report, task_id, state_of):
    rows = report.get('results')
    if not isinstance(rows, list):
        raise ValueError(f'{task_id} report has no results list')
    grouped = {}
    for row in rows:
        if not isinstance(row, dict) or 'variant' not in row:
            continue
        grouped.setdefault(_variant_key(task_id, row['variant']), []).append(row)
    if 'reference' not in grouped or 'baseline' not in grouped:
        raise ValueError(f'{task_id} report is missing reference or baseline')
    reference, baseline = [], []
    for row in grouped['reference']:
        state = state_of(row)
        checks = _row_checks(row, task_id, manifest) if state['ran'] else []
        passed = state['ran'] and state['passed'] and bool(checks) and all(c['passed'] for c in checks)
        reference.append({'passed': passed, 'checks': checks})
    for row in grouped['baseline']:
        state = state_of(row)
        checks = _row_checks(row, task_id, manifest) if state['ran'] else []
        baseline.append({
            'passed': state['ran'] and state['passed'] and bool(checks) and all(c['passed'] for c in checks),
            'checks': checks,
            'runnable': state['ran'] and bool(checks) and not any(c.get('infrastructure_error') for c in checks),
            'reason': None if state['ran'] else state['reason'],
        })
        if state['ran'] and not checks and not state['passed']:
            baseline[-1]['runnable'] = False
            baseline[-1]['reason'] = 'baseline produced no checks'
    mutants = {}
    for mid in manifest['mutants']:
        runs = grouped.get(mid) or []
        mutants[mid] = [_grouped_mutant(state_of(row), _row_checks(row, task_id, manifest)) for row in runs] or [
            {'runnable': False, 'failed': None, 'reason': 'not present in selfcheck report'}
        ]
    return {'reference_runs': reference, 'baseline_runs': baseline, 'mutants': mutants}


def _grouped_mutant(state, checks):
    if any(c.get('infrastructure_error') for c in checks):
        return _nonsemantic('infrastructure_error', 'verifier reported non-assertion error')
    if not state['ran']:
        return {'runnable': False, 'failed': None, 'reason': state['reason'], 'outcome': state.get('outcome', 'infrastructure_error')}
    if state['passed'] and checks and all(c['passed'] for c in checks):
        return {'runnable': True, 'failed': False, 'reason': 'mutant passed the verifier'}
    if state['passed']:
        return {'runnable': True, 'failed': False, 'reason': 'mutant passed the verifier'}
    if not checks:
        return {'runnable': False, 'failed': None, 'reason': 'mutant produced no checks'}
    if not any(c.get('passed') is False for c in checks):
        return _nonsemantic('infrastructure_error', 'nonzero exit without failed assertion')
    return {'runnable': True, 'failed': True, 'reason': None, 'failed_assertions': [c['name'] for c in checks if c.get('passed') is False]}


def _fold_mutant(runs):
    if not runs:
        return {'runnable': False, 'failed': None, 'reason': 'not present in selfcheck report'}
    if any(not run['runnable'] for run in runs):
        reason = next(run['reason'] for run in runs if not run['runnable'])
        return {'runnable': False, 'failed': None, 'reason': reason or 'not runnable'}
    if all(run['failed'] for run in runs):
        return {'runnable': True, 'failed': True, 'reason': None}
    reason = next((run['reason'] for run in runs if run['reason']), 'mutant did not fail')
    return {'runnable': True, 'failed': False, 'reason': reason}


def _failure_outcome(runs):
    for run in runs:
        if run.get('outcome'):
            return run['outcome']
    reason = ' '.join(str(run.get('reason', '')) for run in runs).lower()
    if 'timeout' in reason or 'timed out' in reason:
        return 'timeout'
    if 'compile' in reason:
        return 'compile_error'
    if 'not present' in reason or 'no runs' in reason or 'no checks' in reason:
        return 'missing_report'
    return 'infrastructure_error'


def _mapping(task_id):
    if task_id in EXPLICIT_CRITICAL:
        return 'explicit-critical-check-names'
    return 'acceptance-id'


def _repeat_source(task_id):
    if task_id == 'B02':
        return 'two run_selfcheck.py invocations'
    return 'reference repeats inside one selfcheck'


def evidence_from_normalized(task_id, manifest, normalized, commands, captured_from):
    reference_runs = normalized['reference_runs']
    baseline_runs = normalized['baseline_runs']
    ref_ok = bool(reference_runs) and all(run.get('passed') for run in reference_runs)
    hashes = [_check_hash(run.get('checks') or []) for run in reference_runs]
    repeat_ok = ref_ok and len(reference_runs) >= 2 and len(set(hashes)) == 1
    if repeat_ok:
        agreement, digest = 'structured', hashes[0]
    elif len(reference_runs) >= 2 and len(set(hashes)) > 1:
        agreement, digest = 'mismatch', None
    else:
        agreement, digest = 'unavailable', None
    critical = []
    baseline_ok = bool(baseline_runs)
    baseline_detail = 'Unfixed baseline failed at least one critical check. No separate nop fixture; baseline is this gate.'
    for run in baseline_runs:
        names = [c['name'] for c in run.get('checks') or [] if c.get('critical') and c.get('assertion_failure') is True]
        if not run.get('runnable'):
            baseline_ok = False
            baseline_detail = run.get('reason') or 'baseline was not runnable'
            critical = []
            break
        if run.get('passed') or not names:
            baseline_ok = False
            if run.get('passed'):
                baseline_detail = 'baseline passed the verifier; an unfixed baseline must fail a critical check'
            else:
                failed = [c['name'] for c in run.get('checks') or [] if not c.get('passed')]
                shown = ', '.join(failed[:8]) or 'none recorded'
                baseline_detail = f'baseline did not fail a critical check (failed: {shown})'
            critical = []
            break
        critical.extend(names)
    critical = _unique(critical)
    if not baseline_runs:
        baseline_ok = False
        baseline_detail = 'baseline was not runnable'
    results = []
    for mid in manifest['mutants']:
        runs = normalized['mutants'].get(mid) or []
        folded = _fold_mutant(runs)
        assertions = _unique([name for run in runs for name in run.get('failed_assertions', [])])
        outcome = 'semantic_assertion' if folded['failed'] is True and assertions else ('survived' if folded['runnable'] else _failure_outcome(runs))
        if folded['failed'] is True and not assertions:
            folded = _nonsemantic('infrastructure_error', 'no explicit failed assertion evidence')
            outcome = 'infrastructure_error'
        results.append(dict(folded, id=mid, outcome=outcome, failed_assertions=assertions))
    mutants_ok = bool(results) and all(item['runnable'] and item['failed'] is True for item in results)
    gaps = []
    for item in results:
        if not item['runnable']:
            gaps.append(f"{item['id']}: not runnable ({item['reason']})")
        elif item['failed'] is not True:
            gaps.append(f"{item['id']}: did not fail ({item['reason']})")
    if not ref_ok:
        gaps.append('reference did not pass')
    if not baseline_ok and baseline_runs and not baseline_runs[0].get('runnable', True):
        gaps.append(baseline_detail)
    if len(reference_runs) < 2:
        gaps.append('fewer than two reference runs')
    gates = {
        'reference': {
            'pass': ref_ok,
            'run_count': len(reference_runs),
            'detail': f'{len(reference_runs)} reference run(s) passed' if ref_ok else 'reference did not pass',
        },
        'nop_or_baseline': {
            'pass': baseline_ok,
            'role': 'baseline',
            'variant': 'baseline',
            'mapping': _mapping(task_id),
            'critical_failures': critical,
            'detail': baseline_detail,
        },
        'mutants': {
            'pass': mutants_ok,
            'listed': list(manifest['mutants']),
            'results': results,
            'detail': f'{len(results)} listed mutants failed' if mutants_ok else 'one or more listed mutants did not fail',
        },
        'repeat': {
            'pass': repeat_ok,
            'run_count': len(reference_runs),
            'agreement': agreement,
            'sha256': digest,
            'source': _repeat_source(task_id),
            'detail': (
                f'{len(reference_runs)} reference runs agreed on pass'
                if repeat_ok else 'reference runs did not agree on pass'
            ),
        },
    }
    overall = all(gates[name]['pass'] for name in GATE_NAMES)
    return {
        'schema': SCHEMA,
        'task_id': task_id,
        'trusted_code_only': True,
        'secure_sandbox': False,
        'full_catalog_ready': False,
        'baseline_role': 'baseline',
        'commands': list(commands),
        'captured_from': captured_from,
        'gates': gates,
        'gaps': gaps,
        'pass': overall,
    }


def evidence_from_capture(task_id, manifest, captured, commands, captured_from):
    if task_id == 'B02':
        normalized = _normalize_b02(manifest, captured)
    elif task_id in ('S01', 'S04'):
        normalized = _normalize_silver(task_id, manifest, captured)
    elif task_id == 'S04-spring':
        normalized = _normalize_spring(manifest, captured)
    elif task_id == 'G01':
        normalized = _normalize_g01(manifest, captured)
    elif task_id == 'G05':
        normalized = _normalize_g05(manifest, captured)
    else:
        raise ValueError('unknown M1 task ' + str(task_id))
    return evidence_from_normalized(task_id, manifest, normalized, commands, captured_from)


def gap_evidence(task_id, manifest, reason, commands, captured_from='unavailable'):
    listed = list(manifest.get('mutants') or [])
    results = [
        {'id': mid, 'runnable': False, 'failed': None, 'reason': reason, 'outcome': 'infrastructure_error', 'failed_assertions': []}
        for mid in listed
    ]
    detail = reason
    gates = {
        'reference': {'pass': False, 'run_count': 0, 'detail': detail},
        'nop_or_baseline': {
            'pass': False,
            'role': 'baseline',
            'variant': 'baseline',
            'mapping': _mapping(task_id),
            'critical_failures': [],
            'detail': detail,
        },
        'mutants': {
            'pass': False,
            'listed': listed,
            'results': results,
            'detail': detail,
        },
        'repeat': {
            'pass': False,
            'run_count': 0,
            'agreement': 'unavailable',
            'sha256': None,
            'source': _repeat_source(task_id),
            'detail': detail,
        },
    }
    gaps = [reason]
    gaps.extend(f'{mid}: not runnable ({reason})' for mid in listed)
    return {
        'schema': SCHEMA,
        'task_id': task_id,
        'trusted_code_only': True,
        'secure_sandbox': False,
        'full_catalog_ready': False,
        'baseline_role': 'baseline',
        'commands': list(commands),
        'captured_from': captured_from,
        'gates': gates,
        'gaps': gaps,
        'pass': False,
    }


def evidence_errors(doc, expected_mutants=None):
    errors = []
    if not isinstance(doc, dict):
        return ['evidence is not an object']
    for key in ('schema', 'task_id', 'trusted_code_only', 'secure_sandbox', 'full_catalog_ready', 'baseline_role', 'commands', 'gates', 'gaps', 'pass'):
        if key not in doc:
            errors.append('missing ' + key)
    if errors:
        return errors
    if doc['schema'] != SCHEMA:
        errors.append('schema')
    if doc['task_id'] not in M1_TASK_IDS:
        errors.append('task_id')
    if doc['trusted_code_only'] is not True or doc['secure_sandbox'] is not False or doc['full_catalog_ready'] is not False:
        errors.append('trust or scope flags')
    if doc['baseline_role'] != 'baseline':
        errors.append('baseline_role')
    if not isinstance(doc['commands'], list) or not all(isinstance(item, str) and item for item in doc['commands']):
        errors.append('commands')
    if not isinstance(doc['gaps'], list) or not all(isinstance(item, str) for item in doc['gaps']):
        errors.append('gaps')
    gates = doc['gates']
    if not isinstance(gates, dict):
        return errors + ['gates']
    for name in GATE_NAMES:
        if name not in gates:
            errors.append('missing gate ' + name)
    if errors and any(name not in gates for name in GATE_NAMES):
        return errors
    for name in GATE_NAMES:
        gate = gates[name]
        if not isinstance(gate, dict) or not isinstance(gate.get('pass'), bool):
            errors.append(name + '.pass')
    nop = gates.get('nop_or_baseline')
    if isinstance(nop, dict):
        if nop.get('role') != 'baseline' or nop.get('variant') != 'baseline':
            errors.append('nop_or_baseline role')
        if not isinstance(nop.get('critical_failures'), list):
            errors.append('critical_failures')
        elif nop.get('pass') and not nop['critical_failures']:
            errors.append('passing baseline gate recorded no critical failure')
    mutants = gates.get('mutants')
    if isinstance(mutants, dict):
        listed = mutants.get('listed')
        results = mutants.get('results')
        if not isinstance(listed, list) or not all(isinstance(item, str) and item for item in listed):
            errors.append('mutants.listed')
        elif len(listed) != len(set(listed)):
            errors.append('duplicate mutant id')
        if not isinstance(results, list):
            errors.append('mutants.results')
        else:
            ids = []
            for item in results:
                if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                    errors.append('mutant result')
                    continue
                ids.append(item['id'])
                if not isinstance(item.get('runnable'), bool):
                    errors.append(item['id'] + ' runnable')
                if item.get('outcome') not in ('semantic_assertion', 'survived', 'timeout', 'compile_error', 'startup_error', 'infrastructure_error', 'missing_report'):
                    errors.append(item['id'] + ' outcome')
                if not isinstance(item.get('failed_assertions'), list) or not all(isinstance(name, str) and name for name in item.get('failed_assertions', [])):
                    errors.append(item['id'] + ' failed_assertions')
                if item.get('failed') is True and (item.get('outcome') != 'semantic_assertion' or not item.get('failed_assertions')):
                    errors.append(item['id'] + ' missing semantic assertion evidence')
                failed = item.get('failed')
                reason = item.get('reason')
                if item.get('runnable') is True:
                    if not isinstance(failed, bool):
                        errors.append(item['id'] + ' failed')
                    if failed is True and reason is not None:
                        errors.append(item['id'] + ' reason')
                    if failed is False and not (isinstance(reason, str) and reason):
                        errors.append(item['id'] + ' reason')
                elif item.get('runnable') is False:
                    if failed is not None or not (isinstance(reason, str) and reason):
                        errors.append(item['id'] + ' not runnable')
            if isinstance(listed, list) and ids != listed:
                errors.append('mutant results do not match listed ids')
        if mutants.get('pass') is True:
            if not results or any(not item.get('runnable') or item.get('failed') is not True for item in results or []):
                errors.append('mutants pass disagrees with results')
        if expected_mutants is not None and listed != list(expected_mutants):
            errors.append('listed mutants do not match task.json')
    repeat = gates.get('repeat')
    if isinstance(repeat, dict):
        if not isinstance(repeat.get('run_count'), int):
            errors.append('repeat.run_count')
        if repeat.get('agreement') not in ('structured', 'mismatch', 'unavailable'):
            errors.append('repeat.agreement')
        if repeat.get('pass') is True:
            digest = repeat.get('sha256')
            if repeat.get('run_count', 0) < 2 or repeat.get('agreement') != 'structured':
                errors.append('repeat pass without two agreeing runs')
            if not isinstance(digest, str) or len(digest) != 64 or any(ch not in '0123456789abcdef' for ch in digest):
                errors.append('repeat.sha256')
    reference = gates.get('reference')
    if isinstance(reference, dict) and reference.get('pass') is True and reference.get('run_count', 0) < 1:
        errors.append('reference pass without a run')
    if isinstance(doc.get('pass'), bool) and isinstance(gates, dict) and all(isinstance(gates.get(name), dict) for name in GATE_NAMES):
        expected = all(gates[name].get('pass') is True for name in GATE_NAMES)
        if doc['pass'] is not expected:
            errors.append('overall pass disagrees with gates')
    return errors


def build_summary(docs):
    by_id = {doc.get('task_id'): doc for doc in docs if isinstance(doc, dict)}
    tasks = {}
    for task_id in M1_TASK_IDS:
        doc = by_id.get(task_id)
        if not isinstance(doc, dict):
            tasks[task_id] = None
            continue
        gates = doc.get('gates') if isinstance(doc.get('gates'), dict) else {}
        gate_pass = {name: isinstance(gates.get(name), dict) and gates[name].get('pass') is True for name in GATE_NAMES}
        tasks[task_id] = {
            'pass': doc.get('pass') is True and all(gate_pass.values()),
            'gates': gate_pass,
            'evidence': evidence_rel(task_id),
            'gaps': doc.get('gaps') if isinstance(doc.get('gaps'), list) else [],
        }
    present = [tasks[task_id] for task_id in M1_TASK_IDS]
    return {
        'schema': SUMMARY_SCHEMA,
        'task_ids': list(M1_TASK_IDS),
        'trusted_code_only': True,
        'secure_sandbox': False,
        'full_catalog_ready': False,
        'tasks': tasks,
        'pass': all(item and item['pass'] for item in present),
    }


def summary_errors(summary):
    errors = []
    if not isinstance(summary, dict):
        return ['summary is not an object']
    for key in ('schema', 'task_ids', 'trusted_code_only', 'secure_sandbox', 'full_catalog_ready', 'tasks', 'pass'):
        if key not in summary:
            errors.append('summary missing ' + key)
    if errors:
        return errors
    if summary['schema'] != SUMMARY_SCHEMA or summary['task_ids'] != list(M1_TASK_IDS):
        errors.append('summary identity')
    if summary['trusted_code_only'] is not True or summary['secure_sandbox'] is not False or summary['full_catalog_ready'] is not False:
        errors.append('summary flags')
    tasks = summary['tasks']
    if not isinstance(tasks, dict):
        return errors + ['summary tasks']
    for task_id in M1_TASK_IDS:
        item = tasks.get(task_id)
        if not isinstance(item, dict):
            errors.append('summary missing ' + task_id)
            continue
        if not isinstance(item.get('pass'), bool):
            errors.append(task_id + ' summary pass')
        gates = item.get('gates')
        if not isinstance(gates, dict) or any(name not in gates or not isinstance(gates[name], bool) for name in GATE_NAMES):
            errors.append(task_id + ' summary gates')
        if item.get('evidence') != evidence_rel(task_id):
            errors.append(task_id + ' evidence path')
    if isinstance(summary.get('pass'), bool) and isinstance(tasks, dict):
        expected = all(isinstance(tasks.get(task_id), dict) and tasks[task_id].get('pass') is True for task_id in M1_TASK_IDS)
        if summary['pass'] is not expected:
            errors.append('summary pass disagrees')
    return errors


def _write_json(path, document):
    atomic_json(path, document)


def write_evidence(root, docs, summary):
    root = Path(root)
    base = root / 'engineering/m1-gates/evidence'
    run_id = summary['run_id']
    run_dir = base / 'runs' / run_id
    # Archive the pre-migration successful snapshots before replacing them.
    legacy = base / 'legacy'
    if not legacy.exists() and (base / 'summary.json').exists():
        legacy.mkdir(parents=True)
        (legacy / 'summary.json').write_bytes((base / 'summary.json').read_bytes())
        for task_id in M1_TASK_IDS:
            old = root / evidence_rel(task_id)
            if old.is_file():
                (legacy / (task_id + '.json')).write_bytes(old.read_bytes())
    for doc in docs:
        task_id = doc.get('task_id') if isinstance(doc, dict) else None
        if task_id not in TASK_DIRS:
            continue
        _write_json(run_dir / (task_id + '.json'), doc)
        _write_json(root / evidence_rel(task_id), doc)
    _write_json(run_dir / 'summary.json', summary)
    path = base / 'summary.json'
    _write_json(path, summary)
    _write_json(base / 'latest.json', {'schema': 'm1-latest/v1', 'run_id': run_id,
        'state': 'completed' if summary.get('pass') else 'verification_failed',
        'summary': str((run_dir / 'summary.json').relative_to(root))})
    return path


def _parse_json(text):
    text = (text or '').strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _command_text(argv, root):
    root = Path(root).resolve()
    parts = []
    for part in argv:
        text = str(part)
        path = Path(text)
        if path.is_absolute():
            try:
                text = path.resolve().relative_to(root).as_posix()
            except ValueError:
                if path.name.startswith('python'):
                    text = 'python3'
        parts.append(text)
    return ' '.join(parts)


def default_executor(argv, cwd, timeout):
    from process_supervisor import executor
    return executor(argv, cwd, timeout)


def _h2_ready():
    return Path(os.environ.get('BENCH_H2_JAR', '/tmp/java-agent-bench-h2-2.3.232.jar')).is_file()


def _spring_ready(root):
    lock_path = task_dir(root, 'S04-spring') / 'dependencies.lock.json'
    if not lock_path.is_file():
        return False
    cache = Path(os.environ.get('S04_SPRING_DEPS', '/tmp/java-agent-bench-s04-spring-deps'))
    rows = json.loads(lock_path.read_text())
    return all((cache / row['file']).is_file() for row in rows)


def prepare_plan(root, task_id):
    root = Path(root)
    if task_id == 'S04' and not _h2_ready():
        return [sys.executable, '-B', str(root / 'engineering/silver/setup_h2.py')], root, 180
    if task_id == 'S04-spring' and not _spring_ready(root):
        return [sys.executable, '-B', str(root / 'engineering/integration/S04-spring/tools/bootstrap.py')], task_dir(root, task_id), 240
    return None


def _tail(result):
    text = ((result.get('stderr') or '') + '\n' + (result.get('stdout') or '')).strip()
    if result.get('timeout'):
        text = 'timeout\n' + text
    text = ' '.join(text.split())
    return text[:500] or 'no output'


def java_available(executor):
    try:
        result = executor(['java', '-version'], ROOT, 30)
    except OSError:
        return False
    return result.get('exit') == 0 and not result.get('timeout') and result.get('cleanup_complete', True)


def collect_task(root, task_id, executor):
    root = Path(root)
    folder = task_dir(root, task_id)
    manifest = _load_manifest(root, task_id)
    commands = []
    prep = prepare_plan(root, task_id)
    if prep is not None:
        argv, cwd, timeout = prep
        commands.append(_command_text(argv, root))
        prepared = executor(argv, cwd, timeout)
        if prepared.get('exit') != 0 or prepared.get('timeout'):
            return gap_evidence(task_id, manifest, 'dependency setup failed: ' + _tail(prepared), commands)
    plan = invocation_plan(root, task_id)
    report_rel = REPORT_FILES.get(task_id)
    report_path = folder / report_rel if report_rel else None
    before = report_path.read_bytes() if report_path is not None and report_path.is_file() else None
    if report_path is not None and report_path.exists():
        report_path.unlink()
    results, produced = [], None
    try:
        for argv, timeout in plan:
            commands.append(_command_text(argv, root))
            result = executor(argv, folder, timeout)
            results.append(result)
            if result.get('timeout'):
                break
            if report_rel is None and _parse_json(result.get('stdout')) is None:
                break
        if report_path is not None and report_path.is_file():
            produced = report_path.read_bytes()
    finally:
        if report_path is not None:
            if before is None:
                if report_path.exists():
                    report_path.unlink()
            else:
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_bytes(before)
    if any(result.get('cleanup_complete') is False or result.get('failure') for result in results):
        return gap_evidence(task_id, manifest, 'selfcheck infrastructure failure: ' + _tail(results[-1]), commands, report_rel or 'stdout')
    if any(result.get('timeout') for result in results):
        return gap_evidence(task_id, manifest, 'selfcheck timed out', commands, report_rel or 'stdout')
    if any(result.get('exit') not in (0, 1) for result in results):
        return gap_evidence(task_id, manifest, 'selfcheck did not complete: ' + _tail(results[-1]), commands, report_rel or 'stdout')
    try:
        if task_id == 'B02':
            captured = []
            for result in results:
                parsed = _parse_json(result.get('stdout'))
                if not isinstance(parsed, dict):
                    raise ValueError('selfcheck stdout was not JSON: ' + _tail(result))
                captured.append(parsed)
            if len(captured) != len(plan):
                raise ValueError('B02 did not complete both selfcheck invocations')
            return evidence_from_capture(task_id, manifest, captured, commands, 'stdout')
        if not produced:
            raise ValueError('selfcheck did not refresh ' + (report_rel or 'its report') + ': ' + _tail(results[-1] if results else {}))
        captured = json.loads(produced.decode())
        return evidence_from_capture(task_id, manifest, captured, commands, report_rel)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        return gap_evidence(task_id, manifest, 'could not read selfcheck report: ' + str(exc), commands, report_rel or 'stdout')


def collect_live(root, executor=None):
    root = Path(root)
    executor = executor or default_executor
    if not java_available(executor):
        docs = []
        for task_id in M1_TASK_IDS:
            manifest = _load_manifest(root, task_id)
            docs.append(gap_evidence(task_id, manifest, 'java is not available', ['java -version']))
        return docs
    docs = []
    for task_id in M1_TASK_IDS:
        print(f'=== M1 {task_id} ===', flush=True)
        started = time.monotonic()
        try:
            doc = collect_task(root, task_id, executor)
        except Exception as exc:
            doc = gap_evidence(task_id, {'mutants': mutants_of(root, task_id) or []}, type(exc).__name__ + ': ' + str(exc), [])
        doc['elapsed_seconds'] = round(time.monotonic() - started, 3)
        print(
            task_id + ' ' + ' '.join(f'{name}={"pass" if doc["gates"][name]["pass"] else "fail"}' for name in GATE_NAMES),
            flush=True,
        )
        docs.append(doc)
    return docs


def _now():
    return datetime.now(timezone.utc).isoformat()


def _run_locked(root=None, collect=None):
    root = Path(root) if root is not None else ROOT
    print(WARNING, flush=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-') + uuid.uuid4().hex[:12]
    started = _now()
    base = root / 'engineering/m1-gates/evidence'
    run_dir = base / 'runs' / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    attempt = {'schema': 'm1-attempt/v1', 'run_id': run_id, 'started_at': started,
               'state': 'running', 'python_version': sys.version, 'platform': sys.platform}
    _write_json(run_dir / 'attempt.json', attempt)
    # Publish before fingerprinting or launching anything: an interrupted attempt
    # must invalidate the previous successful selection, even after SIGKILL.
    _write_json(base / 'latest.json', {'schema': 'm1-latest/v1', 'run_id': run_id, 'state': 'running',
                                    'summary': str((run_dir / 'summary.json').relative_to(root))})
    fingerprints, errors = {}, []
    for task_id in M1_TASK_IDS:
        try:
            fingerprints[task_id] = source_fingerprint(root, task_id)
        except (OSError, ValueError) as exc:
            errors.append(task_id + ' fingerprint: ' + str(exc))
    environment = {'python_version': sys.version, 'platform': sys.platform, 'java_version': None,
                   'execution_kind': 'trusted_fixture_selfcheck' if collect is None else 'injected_collector'}
    if collect is None:
        try:
            java = default_executor(['java', '-version'], root, 30)
            environment['java_version'] = ((java.get('stdout') or '') + (java.get('stderr') or '')).strip()
            environment['java_probe_exit'] = java.get('exit')
        except Exception as exc:
            environment['java_probe_error'] = str(exc)
    try:
        docs = (collect or collect_live)(root)
        if not isinstance(docs, list):
            raise ValueError('M1 gate runner returned no report list')
    except (Exception, KeyboardInterrupt) as exc:
        errors.append(type(exc).__name__ + ': ' + str(exc))
        docs = []
    by_id = {doc.get('task_id'): doc for doc in docs if isinstance(doc, dict)}
    docs = []
    for task_id in M1_TASK_IDS:
        doc = by_id.get(task_id)
        manifest = {'mutants': mutants_of(root, task_id) or []}
        if doc is None:
            doc = gap_evidence(task_id, manifest, 'attempt failed: ' + '; '.join(errors), [])
        validation = evidence_errors(doc, mutants_of(root, task_id))
        if validation:
            errors.extend(task_id + ': ' + item for item in validation)
            doc = gap_evidence(task_id, manifest, 'invalid evidence: ' + '; '.join(validation), [])
        fingerprint = fingerprints.get(task_id)
        try:
            if fingerprint is None or source_fingerprint(root, task_id) != fingerprint:
                raise ValueError('source bundle missing or changed during run')
        except (OSError, ValueError) as exc:
            doc = gap_evidence(task_id, manifest, str(exc), doc.get('commands', []))
        doc.update(run_id=run_id, started_at=started, ended_at=_now(), evidence_fingerprint=fingerprint,
                   exit_type='completed' if doc.get('pass') else 'verification_failed')
        docs.append(doc)
    summary = build_summary(docs)
    summary.update(run_id=run_id, started_at=started, ended_at=_now(), errors=errors, environment=environment)
    attempt.update(state='completed' if summary.get('pass') else 'verification_failed', ended_at=summary['ended_at'], environment=environment)
    _write_json(run_dir / 'attempt.json', attempt)
    summary_path = write_evidence(root, docs, summary)
    errors.extend(summary_errors(summary))
    print(f'M1 summary: {summary_path}', flush=True)
    if errors or summary.get('pass') is not True:
        for item in errors:
            print(item, file=sys.stderr)
        print('M1 four-gate check failed', file=sys.stderr)
        return 1
    print('M1 four-gate check passed', flush=True)
    return 0


def run(root=None, collect=None):
    """Serialize latest selection; a competing caller cannot supersede a live run."""
    import fcntl
    root = Path(root) if root is not None else ROOT
    base = root / 'engineering/m1-gates/evidence'
    base.mkdir(parents=True, exist_ok=True)
    with (base / '.run.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('M1 attempt already running; latest selection unchanged', file=sys.stderr)
            return 1
        try:
            return _run_locked(root, collect)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)

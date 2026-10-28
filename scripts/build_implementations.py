"""Generate discovery metadata for runnable slices.

Implementation ``status`` vocabulary:

- ``runnable_slice``: trusted local slice. Four-gate pass is not claimed.
- ``runnable_integration_slice``: integration slice (today S04-spring before
  gates). Four-gate pass is not claimed. Offline-irreproducible dependencies
  stay inside ``scope`` and are not marked ready.
- ``gates_green``: that slice passed the M1 four gates (reference,
  nop_or_baseline, mutants, repeat) in
  ``engineering/m1-gates/evidence/summary.json`` and the per-task
  ``evidence/m1-four-gates.json``. ``slice_kind`` keeps the class above.
  ``full_catalog_ready`` stays false. This is not ``design_ready``,
  ``catalog_ready``, ``production_ready``, or a secure sandbox.

``catalog/tasks.json`` ``status`` stays ``design_only``. Catalog ids that have
a gates_green slice also carry ``slice_implementation`` pointing at those
implementation ids. ``design_only`` does not mean "nothing executable".
``gates_green`` does not mean the original design is catalog-ready.
"""
import json, hashlib, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import m1_gates
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOUR_GATES = ('reference', 'nop_or_baseline', 'mutants', 'repeat')
SUMMARY_REL = 'engineering/m1-gates/evidence/summary.json'
SLICE_KINDS = {'runnable_slice', 'runnable_integration_slice'}
IMPLEMENTATION_STATUSES = SLICE_KINDS | {'gates_green'}


def promoted_from_summary(summary, evidence_for, fingerprint_for=None):
    """Return {task_id: evidence_rel} for slices whose four gates actually passed.

    A summary ``pass`` without matching per-task evidence raises. A task that
    did not pass is omitted. This function never invents a gate pass and never
    treats ``full_catalog_ready`` as true.
    """
    if not isinstance(summary, dict):
        raise SystemExit('m1 summary must be an object')
    if summary.get('schema') != 'm1-four-gates-summary/v1':
        raise SystemExit('m1 summary schema mismatch')
    if summary.get('full_catalog_ready') is not False:
        raise SystemExit('refusing gates_green: summary full_catalog_ready is not false')
    if summary.get('secure_sandbox') is not False or summary.get('trusted_code_only') is not True:
        raise SystemExit('refusing gates_green: summary is not trusted-code-only')
    tasks = summary.get('tasks')
    if not isinstance(tasks, dict):
        raise SystemExit('m1 summary tasks missing')
    promoted = {}
    for task_id, item in tasks.items():
        if not isinstance(item, dict) or item.get('pass') is not True:
            continue
        gates = item.get('gates')
        if not isinstance(gates, dict) or any(gates.get(name) is not True for name in FOUR_GATES):
            continue
        rel = item.get('evidence')
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise SystemExit(f'{task_id} evidence path is not a relative repo path')
        evidence = evidence_for(rel)
        if not isinstance(evidence, dict):
            raise SystemExit(f'{task_id} evidence is not an object')
        if evidence.get('task_id') != task_id or evidence.get('pass') is not True:
            raise SystemExit(f'{task_id} evidence does not confirm the summary pass')
        if evidence.get('full_catalog_ready') is not False or evidence.get('secure_sandbox') is not False or evidence.get('trusted_code_only') is not True:
            raise SystemExit(f'{task_id} evidence is not an honest non-catalog-ready trusted slice')
        egates = evidence.get('gates')
        if not isinstance(egates, dict) or any(
            not isinstance(egates.get(name), dict) or egates[name].get('pass') is not True for name in FOUR_GATES
        ):
            raise SystemExit(f'{task_id} evidence gates are not all green')
        # Unbound legacy captures remain historical facts, never current green.
        if fingerprint_for is None or not summary.get('run_id') or evidence.get('run_id') != summary.get('run_id'):
            continue
        if evidence.get('evidence_fingerprint') != fingerprint_for(task_id):
            continue
        if m1_gates.evidence_errors(evidence):
            continue
        promoted[task_id] = rel
    return promoted


class GateSelection(dict):
    def __init__(self, *args, states=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.states = states or {}


def load_promoted(root):
    root = Path(root)
    states = {tid: ('stale', 'No current source-bound completed attempt') for tid in m1_gates.M1_TASK_IDS}
    selection = GateSelection(states=states)
    latest_path = root / 'engineering/m1-gates/evidence/latest.json'
    if not latest_path.is_file():
        return selection
    try:
        latest = json.loads(latest_path.read_text())
        if not isinstance(latest, dict):
            raise ValueError('latest selector is not an object')
        run_id = latest.get('run_id')
        if not isinstance(run_id, str) or not run_id or '/' in run_id or '..' in run_id:
            raise ValueError('invalid latest run identity')
        expected = f'engineering/m1-gates/evidence/runs/{run_id}/summary.json'
        if latest.get('summary') != expected:
            raise ValueError('latest summary path mismatch')
        if latest.get('state') != 'completed':
            raise ValueError('latest attempt is ' + str(latest.get('state')))
        summary = json.loads((root / expected).read_text())
        if not isinstance(summary, dict) or summary.get('run_id') != run_id or m1_gates.summary_errors(summary):
            raise ValueError('latest summary is invalid')
        def evidence_for(rel):
            task_id = next(tid for tid in m1_gates.M1_TASK_IDS if m1_gates.evidence_rel(tid) == rel)
            evidence = json.loads((root / Path(expected).parent / (task_id + '.json')).read_text())
            # Compatibility views must not silently diverge from selected history.
            if json.loads((root / rel).read_text()) != evidence:
                raise ValueError('compatibility evidence differs from latest attempt')
            return evidence
        def fingerprint_for(task_id):
            return m1_gates.source_fingerprint(root, task_id)
        selection.update(promoted_from_summary(summary, evidence_for, fingerprint_for))
        for task_id, item in summary['tasks'].items():
            if task_id in selection:
                states[task_id] = ('current', 'Current source bundle passed all four gates')
            elif not item or item.get('pass') is not True:
                states[task_id] = ('verification_failed', 'Latest task attempt failed')
    except (OSError, ValueError, KeyError, StopIteration, SystemExit) as exc:
        selection.clear()
        selection.states = {tid: ('verification_failed', str(exc)) for tid in m1_gates.M1_TASK_IDS}
    return selection


def gate_task_id(implementation_id, promoted):
    if implementation_id in promoted:
        return implementation_id
    if implementation_id.endswith('-slice'):
        base = implementation_id[:-len('-slice')]
        if base in promoted:
            return base
    return None


def apply_gate_status(record, promoted):
    kind = record['status']
    if kind not in SLICE_KINDS:
        raise SystemExit(f"unexpected slice status {kind}")
    task_id = gate_task_id(record['implementation_id'], promoted)
    if task_id is None:
        raw_id = record['implementation_id'].removesuffix('-slice')
        state = getattr(promoted, 'states', {}).get(raw_id)
        if state:
            record['gate_status'], record['gate_reason'] = state
        return record
    ordered = {}
    for key, value in record.items():
        ordered[key] = 'gates_green' if key == 'status' else value
        if key == 'status':
            ordered['slice_kind'] = kind
            ordered['full_catalog_ready'] = False
            ordered['gates_evidence'] = promoted[task_id]
    return ordered


def _scope(manifest):
    scope = manifest.get('implemented_scope') or manifest.get('scope') or manifest.get('limitations') or manifest.get('implementedScope') or '以本题 task.json 与 README 标明的范围和局限为准。'
    if not isinstance(scope, str):
        scope = json.dumps(scope, ensure_ascii=False, indent=2)
    return scope


def build_records(root, promoted=None):
    if promoted is None:
        promoted = load_promoted(root)
    records = []
    for tier in ['bronze', 'silver', 'gold', 'diamond', 'king']:
        for path in sorted((root / 'engineering' / tier).glob('[BSGDK]0[1-5]')):
            if not (path / 'task.json').exists() or not (path / 'agent-files.json').exists():
                continue
            manifest = json.loads((path / 'task.json').read_text())
            task_id = path.name
            record = {
                'id': task_id,
                'implementation_id': task_id + '-slice',
                'tier': tier,
                'status': 'runnable_slice',
                'manifest_sha256': hashlib.sha256((path / 'task.json').read_bytes()).hexdigest(),
                'path': str(path.relative_to(root)),
                'scope': _scope(manifest),
                'command': f'python3 scripts/engineering.py prepare {task_id} /tmp/{task_id.lower()}-work\n# 仅在你确认代码可信后执行；正式模型提交需另建隔离环境\npython3 scripts/engineering.py evaluate {task_id} /tmp/{task_id.lower()}-work --trusted-code --output /tmp/{task_id.lower()}-result.json',
                'model_evaluated': False,
                'security': 'not_a_secure_sandbox',
            }
            records.append(apply_gate_status(record, promoted))
    spring = root / 'engineering/integration/S04-spring'
    if (spring / 'task.json').is_file() and (spring / 'agent-files.json').is_file():
        record = {
            'id': 'S04',
            'implementation_id': 'S04-spring',
            'tier': 'silver',
            'status': 'runnable_integration_slice',
            'manifest_sha256': hashlib.sha256((spring / 'task.json').read_bytes()).hexdigest(),
            'path': str(spring.relative_to(root)),
            'scope': '真实 Spring 事务代理 + JDBC/H2；不是 PostgreSQL、HTTP 认证或完整生产连接池验证。详见本题覆盖边界。',
            'command': 'python3 engineering/integration/S04-spring/tools/bootstrap.py\npython3 scripts/engineering.py prepare S04-spring /tmp/s04-spring-work\npython3 scripts/engineering.py evaluate S04-spring /tmp/s04-spring-work --trusted-code --output /tmp/s04-spring-result.json',
            'model_evaluated': False,
            'security': 'not_a_secure_sandbox',
        }
        records.insert(0, apply_gate_status(record, promoted))
    for record in records:
        if record['status'] not in IMPLEMENTATION_STATUSES or 'ready' in record['status']:
            raise SystemExit(f"refusing status {record['status']}")
        if record['security'] != 'not_a_secure_sandbox' or record['model_evaluated'] is not False:
            raise SystemExit(f"{record['implementation_id']} must stay not_a_secure_sandbox and model_evaluated false")
        if record['status'] == 'gates_green':
            if record.get('full_catalog_ready') is not False or record.get('slice_kind') not in SLICE_KINDS:
                raise SystemExit(f"{record['implementation_id']} gates_green record is not honest")
        elif 'full_catalog_ready' in record or 'slice_kind' in record or 'gates_evidence' in record:
            raise SystemExit(f"{record['implementation_id']} must not carry gate fields without gates_green")
    return records


def slice_implementation_link(implementation_ids):
    return {
        'engineering_status': 'gates_green',
        'full_catalog_ready': False,
        'implementations': implementation_ids,
        'evidence': SUMMARY_REL,
    }


def expected_catalog_links(records):
    grouped = {}
    for record in records:
        if record['status'] != 'gates_green':
            continue
        grouped.setdefault(record['id'], []).append(record['implementation_id'])
    return {task_id: slice_implementation_link(ids) for task_id, ids in grouped.items()}


def assert_catalog_links(root, records):
    tasks = json.loads((root / 'catalog/tasks.json').read_text())
    links = expected_catalog_links(records)
    if len(tasks) != 25:
        raise SystemExit('catalog must stay the original 25 designs')
    seen = set()
    for task in tasks:
        task_id = task.get('id')
        seen.add(task_id)
        if task.get('status') != 'design_only':
            raise SystemExit(f'{task_id} catalog status must stay design_only')
        if task.get('full_catalog_ready') is True:
            raise SystemExit(f'{task_id} catalog design claims full_catalog_ready')
        link = task.get('slice_implementation')
        if task_id in links:
            if link != links[task_id]:
                raise SystemExit(f'{task_id} slice_implementation does not match gates_green implementations')
        elif link is not None:
            raise SystemExit(f'{task_id} slice_implementation set without gates_green evidence')
    missing = set(links) - seen
    if missing:
        raise SystemExit('gates_green catalog ids missing from tasks.json: ' + ','.join(sorted(missing)))


def dump(records):
    return json.dumps(records, ensure_ascii=False, indent=2) + '\n'


def main():
    records = build_records(ROOT)
    # Reconcile derived links as well: stale evidence must not leave a green
    # design pointer or prevent writing the downgraded discovery records.
    links = expected_catalog_links(records)
    tasks_path = ROOT / 'catalog/tasks.json'
    tasks = json.loads(tasks_path.read_text())
    for task in tasks:
        task.pop('slice_implementation', None)
        if task['id'] in links:
            task['slice_implementation'] = links[task['id']]
    tasks_text = json.dumps(tasks, ensure_ascii=False, indent=2) + '\n'
    tasks_path.write_text(tasks_text)
    (ROOT / 'dist/tasks.json').write_text(tasks_text)
    assert_catalog_links(ROOT, records)
    text = dump(records)
    (ROOT / 'catalog/implementations.json').write_text(text)
    (ROOT / 'dist/implementations.json').write_text(text)
    green = sum(record['status'] == 'gates_green' for record in records)
    print(f'{len(records)} candidate-adapter slices discovered; {green} gates_green; original catalog statuses remain design_only.')


if __name__ == '__main__':
    main()

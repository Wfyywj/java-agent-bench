"""Contract tests for the M1 four-gate runner. No Java fixture execution."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CE = load('check_engineering_for_m1_tests', 'check_engineering.py')
G = CE.m1_gates


def manifest(task_id, mutants, acceptance):
    return {
        'id': task_id,
        'mutants': list(mutants),
        'original_acceptance': [{'id': item[0], 'critical': item[1]} for item in acceptance],
        'full_catalog_ready': False,
    }


def b02_report(reference_fail=(), baseline_fail=('B02-A01_replay_restart',), mutant_fail=('B02-A02_payload_conflicts',)):
    names = [
        'B02-A01_replay_restart',
        'B02-A02_payload_conflicts',
        'B02-A03_rollback_write_1',
        'B02-A04_tenant_lifecycle',
        'B02-A05_concurrent_http',
    ]

    def variant(failed):
        failed = set(failed)
        return {'passed': not failed, 'checks': {name: ('FAIL: x' if name in failed else 'PASS') for name in names}}

    mutants = ('conflict_ignored', 'partial_commit', 'damaged_available', 'normal_loan_state_omitted')
    variants = {'baseline': variant(baseline_fail), 'reference': variant(reference_fail)}
    variants.update({mid: variant(mutant_fail) for mid in mutants})
    return {'task': 'B02', 'selfcheck': 'PASS', 'variants': variants}


def silver_report(task_id, critical, ordinary, mutants, baseline_fail, mutant_fail):
    def run(failed):
        checks = [
            {'name': 'critical-case', 'acceptance': critical, 'passed': critical not in failed},
            {'name': 'ordinary-case', 'acceptance': ordinary, 'passed': ordinary not in failed},
        ]
        for check in checks:
            check['steps'] = [{'actual': 'ok' if check['passed'] else 'wrong', 'expected': 'ok', 'passed': check['passed']}]
        return {'passed': sum(item['passed'] for item in checks), 'total': len(checks), 'checks': checks}

    variants = {
        'baseline': {'compiled': True, 'runs': [run(baseline_fail)]},
        'reference': {'compiled': True, 'runs': [run(set()), run(set()), run(set())]},
    }
    variants.update({mid: {'compiled': True, 'runs': [run(mutant_fail)]} for mid in mutants})
    return {'id': task_id, 'variants': variants}


def spring_result(fail_name=None):
    names = (
        'active-transaction-at-repository',
        'successful-cancel-atomic-state',
        'checked-mid-batch-rollback',
        'unrelated-batch-preserved',
    )
    lines = []
    for name in names:
        if name == fail_name:
            lines.append(f'FAIL {name} java.lang.AssertionError: no')
        else:
            lines.append('PASS ' + name)
    lines.append('RESULT tests=4 failed=' + ('1' if fail_name else '0'))
    return {
        'passed': fail_name is None,
        'compile': {'exit': 0},
        'test': {'exit': 0 if fail_name is None else 1, 'output': '\n'.join(lines) + '\n'},
    }


def g01_row(variant, repeat, fail_name=None):
    names = ('same request replay one hold', 'recovery audit', 'restart recovery durably releases')
    lines = [('FAIL ' if name == fail_name else 'PASS ') + name for name in names]
    lines.append('INVARIANTS=3 FAILURES=' + ('1' if fail_name else '0'))
    return {
        'variant': variant,
        'repeat': repeat,
        'phase': 'verify',
        'exit': 0 if fail_name is None else 1,
        'passed': fail_name is None,
        'output': '\n'.join(lines) + '\n',
    }


def g05_row(variant, repeat, fail_prefix=None):
    names = ('I01 bounded-worker-budget', 'I02 bounded-queue-budget', 'I03 normal-seat-result')
    lines = []
    for name in names:
        if fail_prefix and name.startswith(fail_prefix):
            lines.append(f'FAIL {name} AssertionError: budget')
        else:
            lines.append('PASS ' + name)
    passed = fail_prefix is None
    lines.append('SUMMARY passed=' + ('3 failed=0' if passed else '2 failed=1'))
    return {
        'variant': variant,
        'repeat': repeat,
        'stage': 'verify',
        'failure': None,
        'incident': {'exit_code': 0, 'failure': None, 'output': 'parents=2\n'},
        'exit_code': 0 if passed else 1,
        'output': '\n'.join(lines) + '\n',
    }


def passing_documents():
    specs = {
        'B02': (
            manifest('B02', (
                'conflict_ignored', 'partial_commit', 'damaged_available', 'normal_loan_state_omitted',
            ), (('B02-A01', True), ('B02-A02', True), ('B02-A03', False))),
            [b02_report(), b02_report()],
            'stdout',
        ),
        'S01': (
            manifest('S01', ('double_booking', 'terminal_regression'), (('S01-A01', True), ('S01-A03', False))),
            silver_report('S01', 'S01-A01', 'S01-A03', ('double_booking', 'terminal_regression'), {'S01-A01'}, {'S01-A01'}),
            'evidence/selfcheck.json',
        ),
        'S04': (
            manifest('S04', ('partial_commit', 'repeat_inventory_change'), (('S04-A01', True), ('S04-A03', False))),
            silver_report('S04', 'S04-A01', 'S04-A03', ('partial_commit', 'repeat_inventory_change'), {'S04-A01'}, {'S04-A01'}),
            'evidence/selfcheck.json',
        ),
        'S04-spring': (
            manifest('S04-spring', ('self-invocation', 'swallow-checked'), ()),
            {
                'baseline': spring_result('active-transaction-at-repository'),
                'reference': [spring_result(), spring_result(), spring_result()],
                'mutants': {mid: spring_result('checked-mid-batch-rollback') for mid in ('self-invocation', 'swallow-checked')},
            },
            'evidence/selfcheck.json',
        ),
        'G01': (
            manifest('G01', ('mutant_release_noop',), (('G01-A02', True),)),
            {'results': [
                *[g01_row('reference', n) for n in (1, 2, 3)],
                *[g01_row('baseline', n, 'restart recovery durably releases') for n in (1, 2, 3)],
                *[g01_row('mutant_release_noop', n, 'restart recovery durably releases') for n in (1, 2, 3)],
            ]},
            'verification-results.json',
        ),
        'G05': (
            manifest('G05', ('shared_bulkhead',), (('G05-A02', True),)),
            {'results': [
                *[g05_row('reference', n) for n in (1, 2, 3)],
                *[g05_row('baseline', n, 'I01') for n in (1, 2, 3)],
                *[g05_row('mutants/shared_bulkhead', n, 'I01') for n in (1, 2, 3)],
            ]},
            'verification-results.json',
        ),
    }
    docs = []
    for task_id in G.M1_TASK_IDS:
        task_manifest, captured, source = specs[task_id]
        docs.append(G.evidence_from_capture(task_id, task_manifest, captured, [f'python3 {task_id}'], source))
    return docs


class M1GateContractTests(unittest.TestCase):
    def test_m1_task_list_is_locked(self):
        self.assertEqual(G.M1_TASK_IDS, ('B02', 'S01', 'S04', 'S04-spring', 'G01', 'G05'))
        fast = (ROOT / 'scripts/check_fast.py').read_text()
        self.assertNotIn('check_engineering', fast)
        self.assertNotIn('--m1', fast)
        for task_id in G.M1_TASK_IDS:
            folder = ROOT / G.TASK_DIRS[task_id]
            document = json.loads((folder / 'task.json').read_text())
            self.assertEqual(document['id'], task_id)
            self.assertIs(document['full_catalog_ready'], False)
            self.assertIsInstance(document['mutants'], list)
            self.assertTrue(document['mutants'])
            script, extra = G.SCRIPTS[task_id]
            self.assertTrue((folder / script).is_file())
            plan = G.invocation_plan(ROOT, task_id)
            self.assertEqual(len(plan), 2 if task_id == 'B02' else 1)
            argv = plan[0][0]
            self.assertNotIn('--candidate', argv)
            self.assertTrue(argv[2].endswith(script))
            self.assertEqual(tuple(argv[3:]), extra)

    def test_modes_do_not_call_the_other_suite(self):
        calls = []
        self.assertEqual(CE.main(['--m1', '--all'], gates_impl=lambda: calls.append('m1') or 0, full_impl=lambda: calls.append('full') or 0), 2)
        self.assertEqual(calls, [])
        self.assertEqual(CE.main([], gates_impl=lambda: 5, full_impl=lambda: 4), 4)
        self.assertEqual(CE.main(['--all'], gates_impl=lambda: 5, full_impl=lambda: 3), 3)
        self.assertEqual(CE.main(['--m1'], gates_impl=lambda: 9, full_impl=lambda: 4), 9)

    def test_synthetic_captures_pass_every_gate(self):
        docs = passing_documents()
        self.assertEqual([doc['task_id'] for doc in docs], list(G.M1_TASK_IDS))
        for doc in docs:
            self.assertEqual(G.evidence_errors(doc), [])
            self.assertTrue(doc['pass'])
            self.assertEqual(doc['baseline_role'], 'baseline')
            self.assertEqual(doc['gates']['nop_or_baseline']['role'], 'baseline')
            self.assertIs(doc['full_catalog_ready'], False)
            self.assertIs(doc['secure_sandbox'], False)
            self.assertGreaterEqual(doc['gates']['repeat']['run_count'], 2)
            self.assertEqual(doc['gaps'], [])

    def test_b02_critical_checks_use_the_acceptance_list(self):
        task_manifest = {
            'id': 'B02',
            'mutants': ['conflict_ignored', 'partial_commit', 'damaged_available', 'normal_loan_state_omitted'],
            'acceptance': [{'id': 'B02-A01', 'critical': True}, {'id': 'B02-A05', 'critical': False}],
        }
        doc = G.evidence_from_capture('B02', task_manifest, [b02_report(), b02_report()], ['a', 'b'], 'stdout')
        self.assertTrue(doc['gates']['nop_or_baseline']['pass'])
        self.assertIn('B02-A01_replay_restart', doc['gates']['nop_or_baseline']['critical_failures'])
        self.assertEqual(G.evidence_errors(doc), [])

    def test_baseline_noncritical_failure_does_not_pass(self):
        task_manifest = manifest('S01', ('double_booking',), (('S01-A01', True), ('S01-A03', False)))
        captured = silver_report('S01', 'S01-A01', 'S01-A03', ('double_booking',), {'S01-A03'}, {'S01-A01'})
        doc = G.evidence_from_capture('S01', task_manifest, captured, ['python3 run_selfcheck.py'], 'evidence/selfcheck.json')
        self.assertFalse(doc['gates']['nop_or_baseline']['pass'])
        self.assertEqual(doc['gates']['nop_or_baseline']['critical_failures'], [])
        self.assertFalse(doc['pass'])
        self.assertEqual(G.evidence_errors(doc), [])

    def test_mutant_that_passes_fails_the_gate(self):
        task_manifest = manifest('B02', ('conflict_ignored', 'partial_commit', 'damaged_available', 'normal_loan_state_omitted'), (('B02-A01', True),))
        good = b02_report()
        leaked = b02_report(mutant_fail=())
        leaked['variants']['conflict_ignored'] = good['variants']['reference']
        doc = G.evidence_from_capture('B02', task_manifest, [good, leaked], ['run', 'run'], 'stdout')
        self.assertFalse(doc['gates']['mutants']['pass'])
        failed = next(item for item in doc['gates']['mutants']['results'] if item['id'] == 'conflict_ignored')
        self.assertTrue(failed['runnable'])
        self.assertFalse(failed['failed'])
        self.assertFalse(doc['pass'])

    def test_missing_mutant_is_recorded(self):
        task_manifest = manifest('S01', ('double_booking', 'terminal_regression'), (('S01-A01', True), ('S01-A03', False)))
        captured = silver_report(
            'S01', 'S01-A01', 'S01-A03', ('double_booking', 'terminal_regression'), {'S01-A01'}, {'S01-A01'},
        )
        del captured['variants']['terminal_regression']
        doc = G.evidence_from_capture('S01', task_manifest, captured, ['python3 run_selfcheck.py'], 'evidence/selfcheck.json')
        missing = next(item for item in doc['gates']['mutants']['results'] if item['id'] == 'terminal_regression')
        self.assertFalse(missing['runnable'])
        self.assertIsNone(missing['failed'])
        self.assertTrue(missing['reason'])
        self.assertTrue(any('terminal_regression' in gap for gap in doc['gaps']))
        self.assertFalse(doc['pass'])

    def test_narrow_entry_fails_when_a_required_field_is_missing(self):
        docs = passing_documents()
        del docs[0]['gates']['repeat']
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = CE.main(['--m1'], gates_impl=lambda: G.run(Path(tmp), collect=lambda root: docs))
            summary = json.loads((Path(tmp) / 'engineering/m1-gates/evidence/summary.json').read_text())
        self.assertEqual(code, 1)
        self.assertIn('missing gate repeat', err.getvalue())
        self.assertFalse(summary['pass'])

    def test_narrow_entry_fails_when_a_mocked_gate_fails(self):
        docs = passing_documents()
        docs[2]['gates']['reference']['pass'] = False
        docs[2]['pass'] = False
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = CE.main(['--m1'], gates_impl=lambda: G.run(Path(tmp), collect=lambda root: docs))
            summary = json.loads((Path(tmp) / 'engineering/m1-gates/evidence/summary.json').read_text())
        self.assertEqual(code, 1)
        self.assertFalse(summary['pass'])
        self.assertFalse(summary['tasks']['S04']['gates']['reference'])
        self.assertIn('M1 four-gate check failed', err.getvalue())

    def test_collect_task_restores_existing_selfcheck_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'engineering/silver/S01'
            (folder / 'evidence').mkdir(parents=True)
            (folder / 'task.json').write_text(json.dumps(manifest(
                'S01', ('double_booking', 'terminal_regression'), (('S01-A01', True), ('S01-A03', False)),
            )))
            prior = folder / 'evidence/selfcheck.json'
            prior.write_text('OLD')
            captured = silver_report('S01', 'S01-A01', 'S01-A03', ('double_booking', 'terminal_regression'), {'S01-A01'}, {'S01-A01'})

            def executor(argv, cwd, timeout):
                self.assertNotIn('--candidate', argv)
                (Path(cwd) / 'evidence/selfcheck.json').write_text(json.dumps(captured))
                return {'argv': argv, 'exit': 0, 'stdout': '', 'stderr': '', 'timeout': False}

            doc = G.collect_task(root, 'S01', executor)
            self.assertEqual(prior.read_text(), 'OLD')
            self.assertTrue(doc['pass'])
            self.assertEqual(G.evidence_errors(doc), [])

    def test_missing_java_records_every_task_without_running_fixtures(self):
        calls = []

        def executor(argv, cwd, timeout):
            calls.append(argv)
            return {'argv': argv, 'exit': 1, 'stdout': '', 'stderr': 'missing java', 'timeout': False}

        docs = G.collect_live(ROOT, executor)
        self.assertEqual([doc['task_id'] for doc in docs], list(G.M1_TASK_IDS))
        self.assertEqual(calls, [['java', '-version']])
        for doc in docs:
            self.assertFalse(doc['pass'])
            self.assertIn('java is not available', doc['gaps'][0])
            self.assertEqual(doc['gates']['mutants']['listed'], mutants(doc['task_id']))
            self.assertTrue(all(item['runnable'] is False for item in doc['gates']['mutants']['results']))


def mutants(task_id):
    return json.loads((ROOT / G.TASK_DIRS[task_id] / 'task.json').read_text())['mutants']


class M1CheckedInEvidenceTests(unittest.TestCase):
    def test_checked_in_evidence_matches_the_locked_contract(self):
        summary_path = ROOT / 'engineering/m1-gates/evidence/summary.json'
        summary = json.loads(summary_path.read_text())
        self.assertEqual(G.summary_errors(summary), [])
        self.assertEqual(summary['task_ids'], list(G.M1_TASK_IDS))
        self.assertIs(summary['full_catalog_ready'], False)
        self.assertIs(summary['secure_sandbox'], False)
        for task_id in G.M1_TASK_IDS:
            path = ROOT / G.evidence_rel(task_id)
            doc = json.loads(path.read_text())
            self.assertEqual(G.evidence_errors(doc, mutants(task_id)), [], task_id)
            self.assertEqual(doc['task_id'], task_id)
            self.assertEqual(summary['tasks'][task_id]['evidence'], G.evidence_rel(task_id))


if __name__ == '__main__':
    unittest.main()

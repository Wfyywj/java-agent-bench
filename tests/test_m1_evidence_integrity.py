"""Offline synthetic regression probes for audit F3/F4/F5; no model calls."""
import copy
import contextlib
import io
import json
import os
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import m1_gates as G
import build_implementations as B
from test_m1_gates import passing_documents, spring_result, silver_report, manifest, b02_report


class EvidenceIntegrityTests(unittest.TestCase):
    def fixture(self, root):
        for doc in passing_documents():
            folder = G.task_dir(root, doc['task_id'])
            folder.mkdir(parents=True)
            (folder / 'task.json').write_text(json.dumps({'mutants': doc['gates']['mutants']['listed']}))
            for name in ('reference/src/A.java', 'baseline/src/A.java', 'mutants/M.java', 'verifier/check.py', 'agent-files.json', 'prompt.md', 'evidence/seed.tsv'):
                p = folder / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('fixture')
        (root / 'scripts').mkdir()
        (root / 'scripts/process_supervisor.py').write_text('fixture')
        (root / 'harness').mkdir()
        (root / 'harness/runner.py').write_text('fixture')

    def run_green(self, root):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return G.run(root, collect=lambda _: passing_documents())

    def test_each_input_change_invalidates_previous_green(self):
        for name in ('reference/src/A.java', 'baseline/src/A.java', 'mutants/M.java', 'verifier/check.py', 'agent-files.json', 'prompt.md', 'task.json', 'evidence/seed.tsv', '@scripts/process_supervisor.py', '@harness/runner.py'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.fixture(root)
                self.assertEqual(self.run_green(root), 0)
                self.assertEqual(set(B.load_promoted(root)), set(G.M1_TASK_IDS))
                p = root / name[1:] if name.startswith('@') else G.task_dir(root, 'B02') / name
                p.write_text(p.read_text() + '\n')
                selected = B.load_promoted(root)
                self.assertNotIn('B02', selected)
                self.assertEqual(selected.states['B02'][0], 'stale')

    def test_added_deleted_renamed_sources_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            before = G.source_fingerprint(root, 'B02')
            p = G.task_dir(root, 'B02') / 'reference/src/New.java'
            p.write_text('new')
            self.assertNotEqual(before, G.source_fingerprint(root, 'B02'))
            p.unlink()
            self.assertEqual(before, G.source_fingerprint(root, 'B02'))
            p = G.task_dir(root, 'B02') / 'reference/src/A.java'
            p.rename(p.with_name('B.java'))
            self.assertNotEqual(before, G.source_fingerprint(root, 'B02'))

    def test_exception_failure_keeps_history_and_selects_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            self.assertEqual(self.run_green(root), 0)
            base = root / 'engineering/m1-gates/evidence'
            old = json.loads((base / 'latest.json').read_text())
            old_bytes = (root / old['summary']).read_bytes()
            def missing_java(_):
                raise FileNotFoundError('java missing')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(G.run(root, collect=missing_java), 1)
            latest = json.loads((base / 'latest.json').read_text())
            self.assertNotEqual(old['run_id'], latest['run_id'])
            self.assertEqual(latest['state'], 'verification_failed')
            self.assertEqual((root / old['summary']).read_bytes(), old_bytes)
            self.assertFalse(json.loads((root / latest['summary']).read_text())['pass'])
            self.assertEqual(B.load_promoted(root), {})

    def test_actual_missing_java_persists_failure_after_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root); self.run_green(root)
            latest_path = root / 'engineering/m1-gates/evidence/latest.json'
            old = json.loads(latest_path.read_text())
            with patch.dict(os.environ, {'PATH': ''}), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(G.run(root), 1)
            latest = json.loads(latest_path.read_text())
            self.assertNotEqual(old['run_id'], latest['run_id'])
            self.assertEqual(latest['state'], 'verification_failed')
            summary = json.loads((root / latest['summary']).read_text())
            self.assertFalse(summary['pass'])
            self.assertTrue(all(not item['pass'] for item in summary['tasks'].values()))
            self.assertTrue(json.loads((root / old['summary']).read_text())['pass'])
            self.assertEqual(B.load_promoted(root), {})

    def test_partial_verifier_output_is_not_a_kill(self):
        for task_id, state_of, row in [
            ('G01', G._g01_state, {'phase': 'verify', 'exit': 1, 'passed': False}),
            ('G05', G._g05_state, {'stage': 'verify', 'failure': None, 'incident': {'exit_code': 0}, 'exit_code': 1}),
        ]:
            row['output'] = 'FAIL partial-check\nException in thread main: boom\n'
            state = state_of(row)
            self.assertFalse(state['ran'], task_id)
            self.assertIsNone(G._grouped_mutant(state, G._status_checks(row['output'], task_id, {}))['failed'])
        result = spring_result('checked-mid-batch-rollback')
        result['test']['output'] = result['test']['output'].split('RESULT')[0]
        self.assertIsNone(G._spring_mutant(result)['failed'])

    def test_running_sentinel_blocks_previous_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root); self.run_green(root)
            def inspect_during_collect(_):
                self.assertEqual(B.load_promoted(root), {})
                self.assertEqual(json.loads((root / 'engineering/m1-gates/evidence/latest.json').read_text())['state'], 'running')
                raise KeyboardInterrupt()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(G.run(root, collect=inspect_during_collect), 1)
            self.assertEqual(B.load_promoted(root), {})

    def test_input_mutation_during_run_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            def mutate(_):
                (G.task_dir(root, 'B02') / 'prompt.md').write_text('changed')
                return passing_documents()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(G.run(root, collect=mutate), 1)
            self.assertEqual(B.load_promoted(root), {})

    def test_competing_attempt_cannot_replace_active_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            def compete(_):
                latest = root / 'engineering/m1-gates/evidence/latest.json'
                before = latest.read_bytes()
                self.assertEqual(G.run(root, collect=lambda _: passing_documents()), 1)
                self.assertEqual(latest.read_bytes(), before)
                return passing_documents()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(G.run(root, collect=compete), 0)
            latest = json.loads((root / 'engineering/m1-gates/evidence/latest.json').read_text())
            attempt = json.loads((root / latest['summary']).with_name('attempt.json').read_text())
            self.assertEqual(attempt['state'], 'completed')

    def test_malformed_selector_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root); self.run_green(root)
            latest = root / 'engineering/m1-gates/evidence/latest.json'
            for bad in ('[]', '{', '{"state":"completed"}'):
                latest.write_text(bad)
                self.assertEqual(B.load_promoted(root), {})

    def test_legacy_unbound_success_not_promotable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.fixture(root)
            base = root / 'engineering/m1-gates/evidence'; base.mkdir(parents=True)
            (base / 'summary.json').write_text(json.dumps(G.build_summary(passing_documents())))
            self.assertEqual(B.load_promoted(root), {})
            old_bytes = (base / 'summary.json').read_bytes()
            self.run_green(root)
            self.assertEqual((base / 'legacy/summary.json').read_bytes(), old_bytes)

    def test_spring_timeout_compile_start_and_missing_are_not_semantic(self):
        for result, expected in [(None, 'missing_report'), ({'compile': {'exit': 1}}, 'compile_error'),
            ({'compile': {'exit': 0}, 'test': {'exit': 124, 'output': 'FAIL x'}}, 'timeout'),
            ({'compile': {'exit': 0}, 'test': {'exit': 2}}, 'startup_error'),
            ({'compile': {'exit': 0}, 'test': {'exit': 1, 'output': ''}}, 'missing_report'),
            ({'compile': {'exit': 0}, 'test': {'exit': 1, 'output': 'ERROR x RuntimeException: bad'}}, 'infrastructure_error')]:
            with self.subTest(expected=expected):
                state = G._spring_mutant(result)
                self.assertIsNone(state['failed']); self.assertEqual(state['outcome'], expected)
        self.assertTrue(G._spring_mutant(spring_result('checked-mid-batch-rollback'))['failed'])

    def test_silver_infrastructure_failure_is_not_assertion(self):
        item = {'compiled': True, 'runs': [{'passed': 0, 'total': 1, 'checks': [{'name': 'case', 'passed': False, 'steps': [{'error': 'process timeout', 'passed': False}]}]}]}
        result = G._mutant_from_silver(item)
        self.assertIsNone(result['failed']); self.assertEqual(result['outcome'], 'timeout')

    def test_silver_requires_completed_comparison_not_just_failed_flag(self):
        def variant(steps):
            return {'compiled': True, 'runs': [{'passed': 0, 'total': 1, 'checks': [{'name': 'case', 'passed': False, 'steps': steps}]}]}
        for steps in ([], [{'passed': False}], [{'passed': False, 'actual': 'wrong'}],
                      [{'passed': False, 'actual': 'ok', 'expected': 'ok'}],
                      [{'passed': False, 'actual': 'wrong', 'expected': 'ok'}, {'passed': True}],
                      [{'passed': False, 'actual': 'ok', 'expected': 'ok', 'jdbc_probe': {'passed': False}}]):
            with self.subTest(steps=steps):
                result = G._mutant_from_silver(variant(steps))
                self.assertIsNone(result['failed'])
                self.assertEqual(result['outcome'], 'missing_report')
        for steps in ([{'passed': False, 'actual': 'wrong', 'expected': 'ok'}],
                      [{'passed': False, 'actual': 'wrong', 'expected': ['ok', 'also-ok']}],
                      [{'passed': False, 'actual': 'ok', 'expected': 'ok', 'jdbc_probe': {'passed': False, 'actual': '2', 'expected': '1'}}]):
            self.assertTrue(G._mutant_from_silver(variant(steps))['failed'])

    def test_completed_report_rejects_duplicate_assertion_names(self):
        for task_id, output in (
            ('G01', 'FAIL same\nFAIL same\nINVARIANTS=2 FAILURES=2'),
            ('G05', 'FAIL same AssertionError: x\nFAIL same AssertionError: y\nSUMMARY passed=0 failed=2'),
            ('S04-spring', 'FAIL same java.lang.AssertionError: x\nFAIL same java.lang.AssertionError: y\nRESULT tests=2 failed=2'),
        ):
            self.assertFalse(G._completed_output(output, task_id))

    def test_b02_error_and_g05_timeout_are_not_assertions(self):
        self.assertIsNone(G._mutant_from_b02({'passed': False, 'checks': {'case': 'ERROR: startup timeout'}}, {})['failed'])
        row = {'stage': 'verify', 'failure': None, 'incident': {'exit_code': 0}, 'exit_code': 124, 'output': 'FAIL I01'}
        result = G._grouped_mutant(G._g05_state(row), G._status_checks(row['output'], 'G05', {}))
        self.assertIsNone(result['failed']); self.assertEqual(result['outcome'], 'timeout')

    def test_kill_claim_requires_named_assertion(self):
        doc = passing_documents()[0]
        doc['gates']['mutants']['results'][0]['failed_assertions'] = []
        self.assertTrue(any('semantic assertion' in e for e in G.evidence_errors(doc)))

    def test_directed_stale_gates_green_repro_blocks(self):
        script = ROOT / 'docs/acceptance/fixtures/directed-counterexamples/stale-gates-green/repro.py'
        run = subprocess.run([sys.executable, str(script)], cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('verdict: blocks', run.stdout)
        self.assertIn('gate_status=stale', run.stdout)
        self.assertNotIn('verdict: still-fails', run.stdout)


if __name__ == '__main__':
    unittest.main()

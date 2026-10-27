"""Discovery status for M1 slices that already passed four gates.

Does not run Java. gates_green is derived from wave B evidence and is not
full catalog ready.
"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M1_CATALOG_IDS = ('B02', 'S01', 'S04', 'G01', 'G05')
M1_IMPLEMENTATIONS = {
    'B02-slice': 'runnable_slice',
    'S01-slice': 'runnable_slice',
    'S04-slice': 'runnable_slice',
    'S04-spring': 'runnable_integration_slice',
    'G01-slice': 'runnable_slice',
    'G05-slice': 'runnable_slice',
}
TASK_JSON = {
    'B02': 'engineering/bronze/B02/task.json',
    'S01': 'engineering/silver/S01/task.json',
    'S04': 'engineering/silver/S04/task.json',
    'S04-spring': 'engineering/integration/S04-spring/task.json',
    'G01': 'engineering/gold/G01/task.json',
    'G05': 'engineering/gold/G05/task.json',
}


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = load('build_implementations_for_status', 'build_implementations.py')
C = load('build_catalog_for_status', 'build_catalog.py')
G = load('m1_gates_for_status', 'm1_gates.py')
E = load('engineering_for_status', 'engineering.py')


def implementations():
    return json.loads((ROOT / 'catalog/implementations.json').read_text())


class M1CatalogStatusTests(unittest.TestCase):
    def test_gate_names_match_the_runner(self):
        self.assertEqual(B.FOUR_GATES, G.GATE_NAMES)

    def test_six_implementations_are_gates_green_and_not_catalog_ready(self):
        records = implementations()
        published = json.loads((ROOT / 'dist/implementations.json').read_text())
        self.assertEqual(records, published)
        self.assertEqual(len(records), 26)
        by_impl = {record['implementation_id']: record for record in records}
        self.assertEqual(len(by_impl), len(records))
        green = [record for record in records if record['status'] == 'gates_green']
        self.assertEqual(sorted(record['implementation_id'] for record in green), sorted(M1_IMPLEMENTATIONS))
        for implementation_id, kind in M1_IMPLEMENTATIONS.items():
            record = by_impl[implementation_id]
            self.assertEqual(record['status'], 'gates_green')
            self.assertEqual(record['slice_kind'], kind)
            self.assertIs(record['full_catalog_ready'], False)
            self.assertIs(record['model_evaluated'], False)
            self.assertEqual(record['security'], 'not_a_secure_sandbox')
            self.assertTrue(record['gates_evidence'].endswith('/evidence/m1-four-gates.json'))
            self.assertTrue((ROOT / record['gates_evidence']).is_file())
            self.assertNotIn('ready', record['status'])
        others = [record for record in records if record['implementation_id'] not in M1_IMPLEMENTATIONS]
        self.assertEqual(len(others), 20)
        for record in others:
            self.assertEqual(record['status'], 'runnable_slice')
            self.assertNotIn('slice_kind', record)
            self.assertNotIn('full_catalog_ready', record)
            self.assertNotIn('gates_evidence', record)
            self.assertIs(record['model_evaluated'], False)
            self.assertEqual(record['security'], 'not_a_secure_sandbox')
        spring = by_impl['S04-spring']
        self.assertIn('不是 PostgreSQL', spring['scope'])
        self.assertIn('完整生产连接池', spring['scope'])
        self.assertEqual(spring['id'], 'S04')

    def test_designs_stay_design_only_with_additive_slice_pointer(self):
        tasks = json.loads((ROOT / 'catalog/tasks.json').read_text())
        self.assertEqual(json.loads((ROOT / 'dist/tasks.json').read_text()), tasks)
        self.assertEqual(len(tasks), 25)
        linked = []
        for task in tasks:
            self.assertEqual(task['status'], 'design_only')
            self.assertIsNot(task.get('full_catalog_ready'), True)
            C.validate_design(task)
            if 'slice_implementation' in task:
                linked.append(task['id'])
                pointer = task['slice_implementation']
                self.assertEqual(pointer['engineering_status'], 'gates_green')
                self.assertIs(pointer['full_catalog_ready'], False)
        self.assertEqual(linked, list(M1_CATALOG_IDS))

    def test_full_catalog_ready_stays_false_on_task_manifests_and_summary(self):
        summary = json.loads((ROOT / B.SUMMARY_REL).read_text())
        self.assertIs(summary['full_catalog_ready'], False)
        self.assertIs(summary['pass'], True)
        self.assertEqual(summary['task_ids'], list(G.M1_TASK_IDS))
        for task_id in G.M1_TASK_IDS:
            document = json.loads((ROOT / TASK_JSON[task_id]).read_text())
            self.assertIs(document['full_catalog_ready'], False)
            self.assertNotEqual(document.get('status'), 'gates_green')
            self.assertNotEqual(document.get('implementation_status'), 'gates_green')
            self.assertNotIn(document.get('implementation_status'), {'ready', 'full_catalog_ready', 'design_only'})

    def test_builder_matches_committed_discovery_files(self):
        records = B.build_records(ROOT)
        B.assert_catalog_links(ROOT, records)
        text = B.dump(records)
        self.assertEqual((ROOT / 'catalog/implementations.json').read_text(), text)
        self.assertEqual((ROOT / 'dist/implementations.json').read_text(), text)
        B.main()
        self.assertEqual((ROOT / 'catalog/implementations.json').read_text(), text)
        self.assertEqual((ROOT / 'dist/implementations.json').read_text(), text)

    def test_missing_evidence_does_not_invent_gates_green(self):
        records = B.build_records(ROOT, promoted={})
        self.assertTrue(all(record['status'] in B.SLICE_KINDS for record in records))
        self.assertFalse(any(record['status'] == 'gates_green' for record in records))
        summary = {
            'schema': 'm1-four-gates-summary/v1',
            'full_catalog_ready': False,
            'secure_sandbox': False,
            'trusted_code_only': True,
            'tasks': {
                'B02': {
                    'pass': False,
                    'gates': {name: False for name in B.FOUR_GATES},
                    'evidence': 'engineering/bronze/B02/evidence/m1-four-gates.json',
                }
            },
        }
        self.assertEqual(B.promoted_from_summary(summary, lambda rel: {}), {})

    def test_summary_cannot_promote_a_disagreeing_or_ready_claim(self):
        claimed = {
            'schema': 'm1-four-gates-summary/v1',
            'full_catalog_ready': False,
            'secure_sandbox': False,
            'trusted_code_only': True,
            'tasks': {
                'B02': {
                    'pass': True,
                    'gates': {name: True for name in B.FOUR_GATES},
                    'evidence': 'engineering/bronze/B02/evidence/m1-four-gates.json',
                }
            },
        }
        evidence = {
            'task_id': 'B02',
            'pass': False,
            'full_catalog_ready': False,
            'secure_sandbox': False,
            'trusted_code_only': True,
            'gates': {name: {'pass': False} for name in B.FOUR_GATES},
        }
        with self.assertRaises(SystemExit):
            B.promoted_from_summary(claimed, lambda rel: evidence)
        ready = dict(claimed, full_catalog_ready=True)
        with self.assertRaises(SystemExit):
            B.promoted_from_summary(ready, lambda rel: evidence)

    def test_design_validator_rejects_ready_vocabulary(self):
        with self.assertRaises(AssertionError):
            C.validate_design({'status': 'gates_green'})
        with self.assertRaises(AssertionError):
            C.validate_design({'status': 'design_only', 'full_catalog_ready': True})
        with self.assertRaises(AssertionError):
            C.validate_design({'status': 'design_only', 'slice_implementation': {
                'engineering_status': 'ready',
                'full_catalog_ready': False,
                'implementations': ['B02-slice'],
                'evidence': B.SUMMARY_REL,
            }})
        with self.assertRaises(AssertionError):
            C.validate_design({'status': 'design_only', 'slice_implementation': {
                'engineering_status': 'gates_green',
                'full_catalog_ready': True,
                'implementations': ['B02-slice'],
                'evidence': B.SUMMARY_REL,
            }})

    def test_list_discovery_uses_gates_green(self):
        rows = {row['implementation_id']: row for row in E.discover()}
        self.assertEqual(len(rows), 26)
        for implementation_id, kind in M1_IMPLEMENTATIONS.items():
            row = rows[implementation_id]
            self.assertEqual(row['status'], 'gates_green')
            self.assertEqual(row['slice_kind'], kind)
            self.assertIs(row['full_catalog_ready'], False)
        self.assertEqual(rows['B01-slice']['status'], 'runnable_slice')
        self.assertNotIn('full_catalog_ready', rows['B01-slice'])
        self.assertNotIn('slice_kind', rows['B01-slice'])


if __name__ == '__main__':
    unittest.main()

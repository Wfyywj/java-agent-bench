"""SYNTHETIC TEST FIXTURES NOT MODEL RESULTS."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from paired_analysis import ValidationError, analyze, load_json

ROOT = Path(__file__).resolve().parent


class PairedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.plan = load_json(ROOT / 'examples/synthetic-plan.json')
        self.records = load_json(ROOT / 'examples/synthetic-records.json')

    def run_analysis(self, **kwargs):
        return analyze(self.plan, self.records, allow_synthetic=True, **kwargs)

    def test_paired_math_and_fixed_denominator(self):
        result = self.run_analysis()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['overall']['success_delta_B_minus_A'], .25)
        self.assertEqual(result['overall']['paired_outcomes'], dict(A_only=1, B_only=2, both_success=1, neither_success=0))
        self.assertEqual(result['overall']['arms']['A']['infrastructure_failures'], 1)
        self.assertEqual(result['overall']['arms']['A']['success_rate'], .5)
        self.assertEqual(result['per_task']['synthetic-task-1']['success_delta_B_minus_A'], 1)
        self.assertEqual(result['per_task']['synthetic-task-2']['success_delta_B_minus_A'], -.5)

    def test_missing_not_dropped(self):
        self.records.pop()
        result = self.run_analysis()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(len(result['missing_slots']), 1)
        self.assertIsNone(result['overall']['success_delta_B_minus_A'])
        self.assertEqual(result['overall']['planned_pairs'], 4)
        self.assertIsNone(result['overall']['arms']['B']['success_rate'])

    def test_empty_records_accounted(self):
        self.records.clear()
        result = self.run_analysis()
        self.assertEqual(len(result['missing_slots']), 8)
        self.assertEqual(result['overall']['arms']['A']['success_rate_bounds'], [0, 1])

    def test_duplicate_slot(self):
        record = copy.deepcopy(self.records[0])
        record['trial_id'] = 'another-id'
        self.records.append(record)
        with self.assertRaisesRegex(ValidationError, 'duplicate slot'):
            self.run_analysis()

    def test_duplicate_trial_id(self):
        self.records[1]['trial_id'] = self.records[0]['trial_id']
        with self.assertRaisesRegex(ValidationError, 'trial_id'):
            self.run_analysis()

    def test_manifest_mismatch(self):
        self.records[0]['manifest_sha256'] = 'e' * 64
        with self.assertRaisesRegex(ValidationError, 'unplanned'):
            self.run_analysis()

    def test_conflicting_plan_versions(self):
        self.plan['pairs'][1]['manifest_sha256'] = 'e' * 64
        with self.assertRaisesRegex(ValidationError, 'conflicting'):
            self.run_analysis()

    def test_duplicate_planned_pair(self):
        self.plan['pairs'].append(copy.deepcopy(self.plan['pairs'][0]))
        with self.assertRaisesRegex(ValidationError, 'duplicate planned'):
            self.run_analysis()

    def test_unknown_cost_keeps_failure(self):
        result = self.run_analysis()['overall']['arms']['A']
        self.assertEqual(result['cost_usd']['unknown_count'], 1)
        self.assertEqual(result['cost_usd']['known_count'], 3)
        self.assertIsNone(result['cost_usd']['total'])
        self.assertAlmostEqual(result['cost_usd']['known_sum'], .03)
        self.assertEqual(result['cost_usd']['unknown_reasons'], {'provider usage unavailable': 1})

    def test_paired_resources_and_elapsed_coverage(self):
        result = self.run_analysis()['overall']['paired_resources']
        self.assertEqual(result['elapsed_seconds']['mean_delta_B_minus_A'], 0)
        self.assertEqual(result['cost_usd']['both_known_pairs'], 3)
        self.assertIsNone(result['cost_usd']['mean_delta_B_minus_A'])
        self.records[0]['elapsed_seconds'] = None
        self.records[0]['elapsed_unknown_reason'] = 'runner timer unavailable'
        result = self.run_analysis()['overall']
        self.assertIsNone(result['arms']['A']['elapsed_seconds']['total'])
        self.assertEqual(result['arms']['A']['elapsed_seconds']['unknown_count'], 1)
        self.assertEqual(result['paired_resources']['elapsed_seconds']['unknown_value_pairs'], 1)
        self.records.pop()
        self.assertEqual(self.run_analysis()['overall']['paired_resources']['elapsed_seconds']['missing_record_pairs'], 1)

    def test_unknown_requires_reason(self):
        self.records[0]['cost_unknown_reason'] = None
        with self.assertRaisesRegex(ValidationError, 'cost_usd'):
            self.run_analysis()

    def test_incompatible_track(self):
        self.plan['arms']['B']['workflow'] = 'different-workflow'
        with self.assertRaisesRegex(ValidationError, 'incompatible'):
            self.run_analysis()

    def test_locked_record_metadata(self):
        self.records[0]['metadata']['budget']['max_tokens'] += 1
        with self.assertRaisesRegex(ValidationError, 'metadata mismatch'):
            self.run_analysis()

    def test_reference_rejected(self):
        for kind in ('selfcheck', 'localreference'):
            self.records[0]['run_kind'] = kind
            with self.assertRaisesRegex(ValidationError, 'not agent trials'):
                self.run_analysis()

    def test_synthetic_opt_in(self):
        with self.assertRaisesRegex(ValidationError, 'allow-synthetic'):
            analyze(self.plan, self.records)

    def test_mixed_data_class_rejected(self):
        self.records[0]['data_class'] = 'actual_agent_trials'
        with self.assertRaisesRegex(ValidationError, 'mixed'):
            self.run_analysis()

    def test_preregistration(self):
        self.records[0]['started_at'] = '2025-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValidationError, 'predates'):
            self.run_analysis()

    def test_evidence_required(self):
        self.records[0]['evidence']['agent_trace_sha256'] = ''
        with self.assertRaisesRegex(ValidationError, 'evidence'):
            self.run_analysis()

    def test_nonfinite_and_bool_rejected(self):
        for value in (float('nan'), float('inf'), True, -1):
            self.records[1]['elapsed_seconds'] = value
            with self.assertRaisesRegex(ValidationError, 'elapsed_seconds'):
                self.run_analysis()

    def test_bootstrap_reproducible_and_incomplete_withheld(self):
        first = self.run_analysis(bootstrap_samples=200)
        self.assertEqual(first, self.run_analysis(bootstrap_samples=200))
        self.assertEqual(first['bootstrap']['seed'], 1729)
        self.assertTrue(any('Small task sample' in x for x in first['warnings']))
        self.records.pop()
        self.assertIsNone(self.run_analysis(bootstrap_samples=200)['bootstrap'])

    def test_json_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'duplicate.json'
            path.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(ValidationError, 'duplicate JSON key'):
                load_json(path)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'records.json'
            for records, flags, expected in [(self.records, [], 1), (self.records, ['--allow-synthetic'], 0), (self.records[:-1], ['--allow-synthetic'], 2)]:
                path.write_text(json.dumps(records))
                run = subprocess.run([sys.executable, str(ROOT/'paired_analysis.py'), '--plan', str(ROOT/'examples/synthetic-plan.json'), '--records', str(path), *flags], capture_output=True, text=True)
                self.assertEqual(run.returncode, expected, run.stderr)
                if expected != 1:
                    self.assertIn('SYNTHETIC TEST FIXTURES NOT MODEL RESULTS', run.stdout)


if __name__ == '__main__':
    unittest.main()

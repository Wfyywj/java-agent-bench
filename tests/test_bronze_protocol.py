"""Candidate-protocol regressions; trusted local fixtures, not sandbox tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'engineering' / 'bronze'


class BronzeCandidateProtocolTests(unittest.TestCase):
    def invoke(self, task, candidate):
        process = subprocess.run([sys.executable, '-B', str(ROOT / task / 'run_selfcheck.py'),
                                  '--candidate', str(candidate)], capture_output=True, text=True, timeout=45)
        self.assertTrue(process.stdout, process.stderr)
        return process.returncode, json.loads(process.stdout)

    def test_b02_reference_passes_and_baseline_is_measured_failure(self):
        for variant, expected in [('reference', 0), ('baseline', 1)]:
            with self.subTest(variant=variant):
                code, result = self.invoke('B02', ROOT / 'B02' / variant)
                self.assertEqual(code, expected, result)
                self.assertEqual(result['passed'], variant == 'reference')
                self.assertEqual(result['status'], 'passed' if expected == 0 else 'verification_failed')

    def test_b02_missing_source_is_invalid_input_not_measured_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, result = self.invoke('B02', Path(tmp))
            self.assertEqual(code, 2)
            self.assertEqual(result['status'], 'input_or_infrastructure_error')

    def test_b04_reviews_artifact_without_compiling_submitted_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            (package / 'review.json').write_text((ROOT / 'B04/reference/review.json').read_text())
            (package / 'src').mkdir()
            (package / 'src/Broken.java').write_text('deliberately not Java; never compiled for review task')
            code, result = self.invoke('B04', package)
            self.assertEqual(code, 0, result)
            self.assertTrue(result['passed'])

    def test_b04_rejects_unjustified_blocker_hidden_among_suggestions(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp)
            review = json.loads((ROOT / 'B04/reference/review.json').read_text())
            review['nonblocking'].append({'kind': 'overflow', 'severity': 'blocking'})
            (package / 'review.json').write_text(json.dumps(review))
            code, result = self.invoke('B04', package)
            self.assertEqual(code, 1, result)
            self.assertFalse(result['passed'])

    def test_b03_accepts_standard_package_root(self):
        code, result = self.invoke('B03', ROOT / 'B03/reference')
        self.assertEqual(code, 0, result)
        self.assertTrue(all(check['pass'] for check in result.values()))
        self.assertIn('B03-A03_limit_bounds', result)

    def test_all_bronze_prepare_whitelists_exclude_grading_assets(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('engineering_prepare', ROOT.parents[1] / 'scripts/engineering.py')
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with tempfile.TemporaryDirectory() as tmp:
            for task in ('B01', 'B02', 'B03', 'B04', 'B05'):
                with self.subTest(task=task):
                    destination = Path(tmp) / task
                    launcher.prepare(task, destination)
                    self.assertTrue((destination / 'src').is_dir())
                    self.assertTrue((destination / 'PROMPT.md').is_file())
                    self.assertFalse((destination / 'reference').exists())
                    self.assertFalse((destination / 'verifier').exists())
                    self.assertFalse((destination / 'run_selfcheck.py').exists())
                    self.assertFalse(list(destination.rglob('*selfcheck*')))
                    self.assertFalse(list(destination.rglob('*contract.json')))

    def test_b04_missing_review_is_invalid_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, result = self.invoke('B04', Path(tmp))
            self.assertEqual(code, 2)
            self.assertEqual(result['status'], 'invalid_input')


if __name__ == '__main__':
    unittest.main()

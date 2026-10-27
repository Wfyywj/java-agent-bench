import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bench', ROOT / 'harness/bench.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class SafetyAndContractTests(unittest.TestCase):
    def test_reject_task_traversal(self):
        for name in ('../R01', '/tmp/R01', 'R01/..', 'R1', 'R01;echo bad'):
            with self.assertRaises(ValueError):
                bench.task(name)

    def test_confined_rejects_absolute_and_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('../out', '/tmp/out', 'a/../../out'):
                with self.assertRaises(ValueError):
                    bench.confined(tmp, name)

    def test_reject_source_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'A.java').write_text('class A {}')
            (root / 'link.java').symlink_to(root / 'A.java')
            with self.assertRaises(ValueError):
                bench.source_files(root)

    def test_missing_java_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                bench.source_files(tmp)

    def test_timeout_kills_process(self):
        result = bench.command([sys.executable, '-c', 'import time; time.sleep(30)'], ROOT, .1)
        self.assertTrue(result['timed_out'])
        self.assertNotEqual(result['exit_code'], 0)
        self.assertLess(result['duration_seconds'], 5)

    def test_output_limit_terminates_chatty_process(self):
        code = 'import os; [os.write(1, b"x"*4096) for _ in range(1000)]'
        result = bench.command([sys.executable, '-c', code], ROOT, 5, output_limit=1024)
        self.assertTrue(result['output_limited'])
        self.assertLessEqual(len(result['stdout']) + len(result['stderr']), 1024)
        self.assertLess(result['duration_seconds'], 5)

    def test_shell_metacharacters_are_data(self):
        value = 'x; echo INJECTED $(id)'
        result = bench.command([sys.executable, '-c', 'import sys; print(sys.argv[1])', value], ROOT, 5)
        self.assertEqual(result['stdout'].strip(), value)

    def test_patch_hash_stable_and_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = Path(tmp) / 'a', Path(tmp) / 'b'
            before.mkdir(); after.mkdir()
            (before / 'A.java').write_text('class A {}\n')
            (after / 'A.java').write_text('class A {}\n')
            initial = bench.patch_hash(before, after)
            self.assertEqual(initial, bench.patch_hash(before, after))
            (after / 'A.java').write_text('class A { int n; }\n')
            self.assertNotEqual(initial, bench.patch_hash(before, after))

    def test_prepare_is_sanitized_and_non_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'work'
            bench.prepare('R01', dest)
            self.assertEqual({p.name for p in dest.iterdir()}, {'src', 'PROMPT.md', 'task.json'})
            self.assertFalse(list(dest.rglob('Verifier.java')))
            self.assertFalse((dest / 'reference').exists())
            self.assertFalse((dest / 'mutation.json').exists())
            with self.assertRaises(ValueError):
                bench.prepare('R01', dest)

    def test_compile_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Broken.java').write_text('not Java at all')
            result = bench.evaluate('R01', tmp)
            self.assertEqual(result['status'], 'build_failed')
            self.assertFalse(result['passed'])
            self.assertEqual(result['checks'], [])

    def test_timeout_limit_rejected(self):
        for timeout in (0, -1, 301, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                bench.evaluate('R01', ROOT, timeout)

    def test_result_schema_contract(self):
        schema = json.loads((ROOT / 'schemas/run-result.schema.json').read_text())
        result = bench.evaluate('R01', ROOT / 'tasks/R01/reference/src')
        self.assertTrue(set(schema['required']).issubset(result))
        self.assertIn(result['status'], schema['properties']['status']['enum'])
        self.assertEqual(len(result['patch_sha256']), 64)
        self.assertTrue(result['passed'])


class RealJavaRegressionTests(unittest.TestCase):
    def test_all_baselines_fail_references_pass_and_mutants_are_killed(self):
        for task_id in ('R01', 'R02', 'R03'):
            with self.subTest(task_id=task_id):
                result = bench.selfcheck(task_id)
                self.assertTrue(result['passed'], json.dumps(result, indent=2))
                self.assertGreaterEqual(len(result['reference']['checks']), 8)
                self.assertTrue(result['mutation_killed'])


if __name__ == '__main__':
    unittest.main()

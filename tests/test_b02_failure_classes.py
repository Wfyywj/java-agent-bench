"""The business oracle must not disguise infrastructure errors as semantic kills."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class FailureClassificationTest(unittest.TestCase):
    def test_business_failure_and_infrastructure_error_are_distinct(self):
        source = Path(__file__).resolve().parents[1] / 'engineering/bronze/B02/verifier/check.py'
        tree = ast.parse(source.read_text())
        check = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'check')
        results = {}

        class Server:
            def __init__(self, directory):
                pass

            def stop(self):
                pass

        namespace = {'results': results, 'Server': Server, 'tempfile': tempfile}
        exec(compile(ast.Module(body=[check], type_ignores=[]), str(source), 'exec'), namespace)

        def business_failure(server):
            raise AssertionError('wrong equipment accepted')

        def infrastructure_failure(server):
            raise RuntimeError('startup timeout')

        namespace['check']('business', business_failure)
        namespace['check']('infrastructure', infrastructure_failure)
        namespace['check']('success', lambda server: None)
        self.assertEqual(results['business'], 'FAIL: wrong equipment accepted')
        self.assertEqual(results['infrastructure'], 'ERROR: RuntimeError: startup timeout')
        self.assertEqual(results['success'], 'PASS')


    def test_selfcheck_rejects_nonsemantic_negative_results(self):
        source = Path(__file__).resolve().parents[1] / 'engineering/bronze/B02/run_selfcheck.py'
        spec = importlib.util.spec_from_file_location('b02_selfcheck', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for checks in ({}, {'case': 'ERROR: RuntimeError: startup timeout'},
                       {'case': 'PASS'}, {'case': 'unexpected'}):
            with self.subTest(checks=checks), patch('sys.argv', [str(source)]), patch.object(
                module, 'bounded', side_effect=[(0, ''), (1, json.dumps(checks))]
            ):
                with self.assertRaises(RuntimeError):
                    module.main()


if __name__ == '__main__':
    unittest.main()

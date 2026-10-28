"""Execute the actual Java test wrappers with isolated assertion/infra failures."""
from pathlib import Path
import ast
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('java'), 'Java is required for wrapper probes')
class VerifierFailureClasses(unittest.TestCase):
    def test_g01_adjacent_capacity_rejection_is_narrow(self):
        source = (ROOT / 'engineering/gold/G01/verifier/Verify.java').read_text()
        helper = source[source.index('static boolean adjacentAccepted('):source.index('static int n=0')]
        probe = '''public class Probe { %s
          public static void main(String[] args) {
            if (!adjacentAccepted(()->{})) throw new AssertionError("success rejected");
            if (adjacentAccepted(()->{throw new IllegalStateException("capacity");})) throw new AssertionError("capacity accepted");
            try {adjacentAccepted(()->{throw new IllegalStateException("disk unavailable");});throw new AssertionError("infra swallowed");}
            catch(IllegalStateException expected) {if(!"disk unavailable".equals(expected.getMessage()))throw expected;}
            try {adjacentAccepted(()->{throw new IllegalArgumentException("unexpected");});throw new AssertionError("unexpected swallowed");}
            catch(IllegalArgumentException expected) {}
          }
        }''' % helper
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'Probe.java'; file.write_text(probe)
            result = subprocess.run(['java', str(file)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_raw_selfchecks_require_completed_assertion_failure(self):
        for path, exit_key, count, marker in (
            ('engineering/integration/S04-spring/run_selfcheck.py', 'exit', 20, 'RESULT tests=20 failed=1'),
            ('engineering/gold/G05/selfcheck.py', 'exit_code', 16, 'SUMMARY passed=15 failed=1'),
            ('engineering/gold/G01/selfcheck.py', 'exit', 3, 'INVARIANTS=3 FAILURES=1'),
        ):
            tree = ast.parse((ROOT / path).read_text())
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'semantic_failure')
            namespace = {}
            exec(compile(ast.Module(body=[function], type_ignores=[]), path, 'exec'), namespace)
            check = namespace['semantic_failure']
            def result(code, output, **extra):
                row = {exit_key: code, 'phase': 'verify', 'output': output, **extra}
                return {'compile': {'exit': 0}, 'test': row} if 'S04-spring' in path else row
            with self.subTest(path=path):
                complete = 'FAIL contract AssertionError: bad\n' + ''.join(f'PASS check-{n}\n' for n in range(count-1)) + marker + '\n'
                self.assertTrue(check(result(1, complete)))
                self.assertFalse(check(result(1, 'FAIL contract AssertionError: bad\n')))
                self.assertFalse(check(result(1, complete.replace(marker, marker+'wrong'))))
                self.assertFalse(check(result(124, 'FAIL contract AssertionError: bad\n')))
                self.assertFalse(check(result(1, 'ERROR infra TimeoutException: expired\n')))
                self.assertFalse(check(result(1, 'FAIL contract AssertionError: bad\nERROR infra SQLException\n')))
                self.assertFalse(check(result(1, '', failure='output_limit')))

    def test_java_wrappers_distinguish_assertions_from_errors(self):
        cases = (
            ('engineering/integration/S04-spring/regression-tests/bench/IntegrationVerifier.java',
             'interface Checked { void run() throws Exception; }',
             'static java.util.List<String> failures=new java.util.ArrayList<>();',
             'failures.size()'),
            ('engineering/gold/G05/verifier/Verify.java',
             'interface Test { void run() throws Exception; }',
             'static int passed,failed;', 'failed'),
        )
        for path, interface, fields, count in cases:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                source = (ROOT / path).read_text()
                start = source.index('static void test(')
                brace = source.index('{', start)
                depth = 1
                end = brace + 1
                while depth:
                    depth += (source[end] == '{') - (source[end] == '}')
                    end += 1
                wrapper = source[start:end]
                probe = ('public class Probe {' + interface + fields + wrapper +
                         'public static void main(String[] args) {'
                         'test("assertion",()->{throw new AssertionError("contract");});'
                         'test("infra",()->{throw new java.sql.SQLException("connection unavailable");});'
                         'test("timeout",()->{throw new java.util.concurrent.TimeoutException("deadline");});'
                         'System.out.println("failures="+' + count + ');}}')
                file = Path(tmp) / 'Probe.java'
                file.write_text(probe)
                result = subprocess.run(['java', str(file)], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('FAIL assertion ', result.stdout)
                self.assertIn('ERROR infra ', result.stdout)
                self.assertIn('ERROR timeout ', result.stdout)
                self.assertIn('failures=3', result.stdout)
                self.assertNotIn('FAIL infra ', result.stdout)


if __name__ == '__main__':
    unittest.main()

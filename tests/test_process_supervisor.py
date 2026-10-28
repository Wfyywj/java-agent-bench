"""Real safe-process regressions; no Java, network, installation or credentials."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import process_supervisor as supervisor


def stopped(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z'
    except FileNotFoundError:
        return True


@unittest.skipUnless(sys.platform == 'linux' and hasattr(os, 'pidfd_open')
                     and hasattr(signal, 'pidfd_send_signal'),
                     'real lifecycle regressions require Linux subreaper/pidfds')
class ProcessSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='owned-process-test-')
        self.addCleanup(self.tmp.cleanup)
        self.pidfile = Path(self.tmp.name) / 'owned.pid'
        # The descendant deliberately starts a distinct session, as nested Java
        # selfchecks do. Its safe sleep is bounded even if the test fails.
        child = ('import os,time,pathlib; '
                 f'pathlib.Path({str(self.pidfile)!r}).write_text(str(os.getpid())); '
                 'time.sleep(15)')
        self.spawn = ('import subprocess,sys,time; '
                      f'subprocess.Popen([sys.executable,"-c",{child!r}],start_new_session=True); ')
        self.addCleanup(self.emergency_cleanup)

    def emergency_cleanup(self):
        # Only an explicitly recorded test-owned PID; pin before signaling.
        if self.pidfile.exists():
            pid = int(self.pidfile.read_text())
            if not stopped(pid):
                try:
                    fd = os.pidfd_open(pid)
                    try:
                        signal.pidfd_send_signal(fd, signal.SIGKILL)
                    finally:
                        os.close(fd)
                except ProcessLookupError:
                    pass

    def wait_file(self):
        deadline = time.monotonic() + 5
        while not self.pidfile.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.pidfile.exists(), 'owned child never started')
        return int(self.pidfile.read_text())

    def assert_child_stopped(self):
        pid = self.wait_file()
        deadline = time.monotonic() + 5
        while not stopped(pid) and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(stopped(pid), f'owned child {pid} survived')

    def run_code(self, code, **kwargs):
        return supervisor.executor([sys.executable, '-c', code], self.tmp.name, **kwargs)

    def test_success_and_stderr(self):
        result = self.run_code('import sys; print("hello"); print("err", file=sys.stderr)', timeout=2)
        self.assertEqual(result['exit'], 0)
        self.assertEqual(result['stdout'], 'hello\n')
        self.assertEqual(result['stderr'], 'err\n')
        self.assertTrue(result['cleanup_complete'])

    def test_timeout_cleans_detached_descendant_not_unrelated_child(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(15)'])
        try:
            start = time.monotonic()
            result = self.run_code(self.spawn + 'time.sleep(15)', timeout=.4)
            self.assertEqual(result['exit'], 124)
            self.assertTrue(result['timeout'])
            self.assertTrue(result['cleanup_complete'])
            self.assertLess(time.monotonic() - start, 5)
            self.assert_child_stopped()
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.kill()
            unrelated.wait(timeout=3)

    def test_exact_g05_nested_runner_timeout(self):
        child = ('import os,time,pathlib; '
                 f'pathlib.Path({str(self.pidfile)!r}).write_text(str(os.getpid())); '
                 'time.sleep(15)')
        code = ('import importlib.util; '
                f's=importlib.util.spec_from_file_location("g05",{str(ROOT / "engineering/gold/G05/selfcheck.py")!r}); '
                'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                f'm.run({[sys.executable, "-c", child]!r}, {self.tmp.name!r}, 10)')
        result = self.run_code(code, timeout=.5)
        self.assertEqual(result['exit'], 124)
        self.assertTrue(result['cleanup_complete'])
        self.assert_child_stopped()

    def test_normal_parent_exit_still_cleans_detached_child(self):
        result = self.run_code(self.spawn + 'time.sleep(.15)', timeout=2)
        self.assertEqual(result['exit'], 0)
        self.assertTrue(result['cleanup_complete'])
        self.assert_child_stopped()

    def test_output_limit_cleans_descendant(self):
        result = self.run_code(self.spawn + 'time.sleep(.15); print("x" * 200000,flush=True); time.sleep(15)',
                               timeout=3, output_limit=1024)
        self.assertEqual(result['failure'], 'output_limit')
        self.assertLessEqual(len(result['stdout']), 1024)
        self.assertTrue(result['cleanup_complete'])
        self.assert_child_stopped()

    def test_launch_error_is_explicit(self):
        result = supervisor.executor(['/definitely-not-a-command'], self.tmp.name, 1)
        self.assertEqual(result['exit'], 127)
        self.assertEqual(result['failure'], 'launch_error')
        self.assertTrue(result['cleanup_complete'])

    def caller(self):
        code = ('import sys; '
                f'sys.path.insert(0,{str(ROOT / "scripts")!r}); '
                'from process_supervisor import executor; '
                f'executor({[sys.executable, "-c", self.spawn + "time.sleep(15)"]!r}, {self.tmp.name!r}, 10)')
        proc = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        def stop():
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=5)
        self.addCleanup(stop)
        return proc

    def test_keyboard_interrupt_cleans_before_propagating(self):
        caller = self.caller()
        self.wait_file()
        caller.send_signal(signal.SIGINT)
        _, err = caller.communicate(timeout=6)
        self.assertIn(b'KeyboardInterrupt', err)
        self.assert_child_stopped()

    def test_caller_death_triggers_helper_cleanup(self):
        caller = self.caller()
        self.wait_file()
        caller.terminate()
        caller.communicate(timeout=6)
        self.assert_child_stopped()

    def test_unexpected_caller_exception_cleans_before_propagating(self):
        real = subprocess.Popen.communicate
        first = True
        def injected(proc, *args, **kwargs):
            nonlocal first
            if first:
                first = False
                self.wait_file()
                raise RuntimeError('injected caller error')
            return real(proc, *args, **kwargs)
        with patch.object(subprocess.Popen, 'communicate', injected):
            with self.assertRaisesRegex(RuntimeError, 'injected caller error'):
                self.run_code(self.spawn + 'time.sleep(15)', timeout=10)
        self.assert_child_stopped()

    def test_unsupported_platform_does_not_launch_workload(self):
        request = dict(argv=[sys.executable, '-c', f'open({str(self.pidfile)!r},"w").write("bad")'],
                       cwd=self.tmp.name, parent=os.getppid(), timeout=1, output_limit=1024)
        with patch.object(supervisor.sys, 'platform', 'unsupported'), patch.object(supervisor.signal, 'signal'):
            result = supervisor._run(request)
        self.assertEqual(result['failure'], 'unsupported_supervisor')
        self.assertFalse(self.pidfile.exists())


class FullSuiteSupervisorTests(unittest.TestCase):
    def test_every_full_suite_runner_uses_supervisor(self):
        import check_engineering
        from contextlib import redirect_stdout, redirect_stderr
        import io
        result = dict(exit=0, stdout='', stderr='', cleanup_complete=True, failure=None)
        with patch.object(check_engineering, 'executor', return_value=result) as execute, \
                patch.object(Path, 'exists', return_value=True), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(check_engineering.run_full_suite(), 0)
        self.assertEqual(execute.call_count, 6)
        self.assertEqual([c.args[2] for c in execute.call_args_list], [600]*5 + [240])
        self.assertTrue(all(c.args[1] == check_engineering.ROOT for c in execute.call_args_list))

    def test_incomplete_cleanup_cannot_be_success(self):
        import check_engineering
        result = dict(exit=0, stdout='', stderr='', cleanup_complete=False, failure='cleanup_failed')
        with patch.object(check_engineering, 'executor', return_value=result):
            with self.assertRaisesRegex(SystemExit, 'cleanup_failed'):
                check_engineering._run_check(['unused'], 'test', 1)


if __name__ == '__main__':
    unittest.main()

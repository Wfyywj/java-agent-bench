#!/usr/bin/env python3
"""Bounded lifecycle for trusted local checks, NOT a hostile-code sandbox.

A separate Linux subreaper owns each command and adopts detached descendants.
Only its direct children are signaled, using pidfds (never process names/groups).
The caller's unrelated children cannot be adopted by this helper. Linux prctl,
pidfds and readable /proc are required; otherwise no workload is launched.
SIGTERM/SIGINT, caller death, timeout, output limit, and normal exit all trigger
cleanup. SIGKILL of the helper itself and uninterruptible kernel tasks are not
containment guarantees; cleanup failure is explicit and cannot produce success.
"""
import ctypes
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

OUTPUT_LIMIT = 4 * 1024 * 1024
CLEANUP_TIMEOUT = 3.0
POLL = 0.02


def _children():
    """Read direct-child identities; disappearance during enumeration is normal."""
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[1]) == os.getpid():
                found.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return found


def _setup(parent):
    if sys.platform != 'linux' or not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Linux subreaper, /proc and pidfd support required')
    libc = ctypes.CDLL(None, use_errno=True)
    for option, value in ((36, 1), (1, signal.SIGTERM)):  # SUBREAPER, PDEATHSIG
        if libc.prctl(option, value, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), 'prctl lifecycle setup failed')
    fd = os.pidfd_open(os.getpid())
    try:
        signal.pidfd_send_signal(fd, 0)
    finally:
        os.close(fd)
    _children()  # Verify /proc before starting anything.
    if os.getppid() != parent:
        raise RuntimeError('caller exited before lifecycle setup')


def _cleanup(proc=None):
    """Kill/reap children, then newly adopted grandchildren, within a bound."""
    deadline = time.monotonic() + CLEANUP_TIMEOUT
    while True:
        for pid in _children():
            try:
                fd = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            try:
                # Recheck ownership after pinning identity; never signal a reused
                # unrelated PID, even if the /proc enumeration raced an exit.
                if pid in _children():
                    signal.pidfd_send_signal(fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                os.close(fd)
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if proc is not None and pid == proc.pid:
                    proc.returncode = os.waitstatus_to_exitcode(status)
            except ChildProcessError:
                return True
            if pid == 0:
                break
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL)


def _run(request):
    result = dict(argv=request['argv'], exit=125, stdout='', stderr='',
                  timeout=False, failure=None, cleanup_complete=True)
    cancelled = []
    def cancel(signum, _frame):
        cancelled.append(signum)
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    try:
        _setup(request['parent'])
    except Exception as exc:
        result.update(failure='unsupported_supervisor', stderr=str(exc))
        return result
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = None
        try:
            if cancelled:
                result.update(exit=130, failure='cancelled')
            else:
                proc = subprocess.Popen(request['argv'], cwd=request['cwd'],
                                        stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                        start_new_session=True)
                deadline = time.monotonic() + request['timeout']
                while True:
                    code = proc.poll()
                    size = os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size
                    if cancelled:
                        result.update(exit=130, failure='cancelled')
                        break
                    if size > request['output_limit']:
                        result.update(exit=125, failure='output_limit')
                        break
                    if code is not None:
                        result['exit'] = code
                        break
                    if time.monotonic() >= deadline:
                        result.update(exit=124, timeout=True, failure='timeout')
                        break
                    time.sleep(POLL)
        except OSError as exc:
            result.update(exit=127, failure='launch_error', stderr=str(exc))
        except BaseException as exc:
            result.update(exit=125, failure='supervisor_error', stderr=str(exc))
        finally:
            try:
                result['cleanup_complete'] = _cleanup(proc)
            except Exception as exc:
                result['cleanup_complete'] = False
                result['stderr'] += '\ncleanup: ' + str(exc)
            if not result['cleanup_complete']:
                result.update(exit=125, failure='cleanup_failed')
        out.seek(0)
        err.seek(0)
        result['stdout'] = out.read(request['output_limit']).decode(errors='replace')
        result['stderr'] += err.read(request['output_limit']).decode(errors='replace')
    return result


def executor(argv, cwd, timeout, *, output_limit=OUTPUT_LIMIT):
    """Return default_executor-compatible evidence; propagate caller exceptions
    only after requesting and awaiting bounded owned-process cleanup.
    """
    timeout = float(timeout)
    if not math.isfinite(timeout) or timeout <= 0 or output_limit <= 0:
        raise ValueError('timeout and output_limit must be finite positive bounds')
    request = dict(argv=[str(arg) for arg in argv], cwd=str(cwd), timeout=timeout,
                   output_limit=int(output_limit), parent=os.getpid())
    helper = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker',
                               json.dumps(request)], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        # The helper enforces the workload deadline. This outer bound handles
        # helper failure, without ever waiting indefinitely on inherited pipes.
        out, err = helper.communicate(timeout=timeout + CLEANUP_TIMEOUT + 5)
    except subprocess.TimeoutExpired:
        helper.terminate()
        try:
            helper.communicate(timeout=CLEANUP_TIMEOUT + 2)
        except subprocess.TimeoutExpired:
            helper.kill()
            helper.communicate(timeout=2)
        return dict(argv=request['argv'], exit=125, stdout='',
                    stderr='supervisor exceeded its bounded response deadline',
                    timeout=False, failure='supervisor_error', cleanup_complete=False)
    except BaseException:
        helper.terminate()
        try:
            helper.communicate(timeout=CLEANUP_TIMEOUT + 2)
        except subprocess.TimeoutExpired:
            helper.kill()
            helper.communicate(timeout=2)
        raise
    try:
        result = json.loads(out)
        if not isinstance(result, dict) or 'cleanup_complete' not in result:
            raise ValueError('invalid supervisor report')
        return result
    except (ValueError, TypeError):
        return dict(argv=request['argv'], exit=125, stdout='', stderr=err or 'missing supervisor report',
                    timeout=False, failure='supervisor_error', cleanup_complete=False)


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--worker':
        raise SystemExit('internal worker; import executor() instead')
    try:
        print(json.dumps(_run(json.loads(sys.argv[2]))), flush=True)
    except BrokenPipeError:
        pass  # Caller is gone; lifecycle cleanup has already run.

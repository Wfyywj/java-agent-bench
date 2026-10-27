"""Runs only checked-in trusted fixture selfchecks, never model submissions.
Not a secure sandbox. The outer runner's timeout/resource policy still applies.
"""
from pathlib import Path
import subprocess,sys,os,time,signal,tempfile
ROOT=Path(__file__).resolve().parents[1]
for tier in ('bronze','silver','gold','diamond','king'):
    runner=ROOT/'engineering'/tier/'run_all.py'
    if not runner.exists():
        print(f'{tier}: suite not implemented; skipped (not a pass)',flush=True);continue
    print(f'=== {tier} ===',flush=True)
    with tempfile.TemporaryFile() as out:
        p=subprocess.Popen([sys.executable,'-B',str(runner)],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+600
        while p.poll() is None:
            if time.monotonic()>deadline or os.fstat(out.fileno()).st_size>4*1024*1024:
                os.killpg(p.pid,signal.SIGKILL);p.wait();raise SystemExit(f'{tier}: time/output limit')
            time.sleep(.2)
        out.seek(0);print(out.read(4*1024*1024).decode(errors='replace'))
        if p.returncode:raise SystemExit(f'{tier}: failed ({p.returncode})')

# Optional real-framework integration variant, with dependencies prewarmed separately.
spring=ROOT/'engineering/integration/S04-spring/run_selfcheck.py'
if spring.exists():
    print('=== S04-spring integration ===',flush=True)
    result=subprocess.run([sys.executable,'-B',str(spring)],cwd=ROOT,timeout=240)
    if result.returncode:raise SystemExit('S04-spring failed')

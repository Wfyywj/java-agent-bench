"""Aggregate trusted local selfchecks, not model submission execution."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent
for task in ('G01','G02','G03','G04','G05'):
    print(f'=== {task} ===',flush=True)
    result=subprocess.run([sys.executable,'-B',str(ROOT/task/'selfcheck.py')],cwd=ROOT/task,timeout=180)
    if result.returncode:raise SystemExit(result.returncode)

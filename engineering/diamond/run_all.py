"""Aggregate trusted local selfchecks, not model submission execution."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent
for task in ('D01','D02','D03','D04','D05'):
    print(f'=== {task} ===',flush=True)
    result=subprocess.run([sys.executable,'-B',str(ROOT/task/'run_selfcheck.py')],cwd=ROOT/task,timeout=180)
    if result.returncode:raise SystemExit(result.returncode)

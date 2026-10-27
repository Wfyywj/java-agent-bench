"""Replay original PR smoke without claiming comprehensive correctness."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_selfcheck import exercise, ROOT
_, outputs, _ = exercise(ROOT/'baseline/src')
assert outputs['smoke']=='OK\t33.00'
print('original candidate smoke PASS')

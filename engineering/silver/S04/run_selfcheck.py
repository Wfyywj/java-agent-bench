#!/usr/bin/env python3
from pathlib import Path
import sys,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from verifier import selfcheck,evaluate_candidate
p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path);a=p.parse_args()
task=Path(__file__).resolve().parent
if a.candidate:
 r=evaluate_candidate(task,a.candidate);print(json.dumps(r));raise SystemExit(0 if r['passed'] else 1)
r=selfcheck(task)
print(json.dumps({'id':r['id'],'passed':r['selfcheck_passed'],'evidence':'evidence/selfcheck.json'}))
raise SystemExit(0 if r['selfcheck_passed'] else 1)

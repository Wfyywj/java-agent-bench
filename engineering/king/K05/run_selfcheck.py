#!/usr/bin/env python3
import sys,json,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from candidate_runner import evaluate
from run_all import run
p=argparse.ArgumentParser();p.add_argument('--candidate');p.add_argument('--repeats',type=int,default=3);a=p.parse_args()
if a.candidate:
 r=evaluate('K05',a.candidate);print(json.dumps(r));sys.exit(0 if r['pass'] else 1)
r=run('K05',a.repeats);print(json.dumps({'task':'K05','all_expected':r['all_expected']}));sys.exit(0 if r['all_expected'] else 1)

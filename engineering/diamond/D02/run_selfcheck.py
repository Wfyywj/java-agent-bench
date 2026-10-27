#!/usr/bin/env python3
import argparse,pathlib,json,run
p=argparse.ArgumentParser();p.add_argument('--candidate');a=p.parse_args()
if a.candidate:
 root=pathlib.Path(a.candidate).resolve();src=root/'src' if (root/'src').is_dir() else root
 r=run.evaluate(src)
 suite=(root/'artifacts/suite.json') if (root/'src').is_dir() else root.parent/'artifacts/suite.json'
 import subprocess
 if suite.exists():
  try:
   completed=subprocess.run(['python3',str(pathlib.Path(__file__).parent/'verifier/evaluate_suite.py'),str(suite)],capture_output=True,text=True,timeout=120)
   r['generated_suite']=json.loads(completed.stdout);r['pass']=r['pass'] and completed.returncode==0
  except Exception as e:r['pass']=False;r['suite_failure']=str(e)
 else:r['pass']=False;r['suite_failure']='artifacts/suite.json required for test-engineering task'
 print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
raise SystemExit(run.main())

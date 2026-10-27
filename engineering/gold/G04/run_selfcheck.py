#!/usr/bin/env python3
import argparse,json,sys
import run
p=argparse.ArgumentParser(description="Evaluate TRUSTED Java candidate. Not a security sandbox.");p.add_argument('--candidate',required=True);a=p.parse_args()
try:
 r=run.run(a.candidate);print(json.dumps(r));sys.exit(0 if r['passed'] else 1)
except Exception as e:
 print(json.dumps({'passed':False,'error':str(e)}));sys.exit(2)

#!/usr/bin/env python3
"""Evaluate an arbitrary trusted source package; JSON stdout, exit 0 iff passing."""
import argparse, hashlib, json, pathlib
from selfcheck import ROOT, verify

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True,type=pathlib.Path);a=p.parse_args()
    try:
        for name,digest in json.loads((ROOT/'fixture-lock.json').read_text()).items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('immutable fixture modified: '+name)
        candidate=a.candidate.resolve()
        if not (candidate/'src').is_dir():raise ValueError('candidate must contain src/bench/Service.java')
        result=verify(str(candidate),1)
        passed=result['stage']=='verify' and result['exit_code']==0 and result['failure'] is None and result['incident']['exit_code']==0
        print(json.dumps({'task':'G05','candidate':str(candidate),'passed':passed,'public_development_only':True,'result':result}))
        return 0 if passed else 1
    except Exception as error:
        print(json.dumps({'task':'G05','passed':False,'error':str(error)}));return 1
if __name__=='__main__':raise SystemExit(main())

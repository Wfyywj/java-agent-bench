#!/usr/bin/env python3
"""Trusted local code only; caps/timeouts are operational limits, not a sandbox."""
from pathlib import Path
import argparse,json,tempfile,shutil,hashlib,datetime,sys
from verify import bounded,verify
ROOT=Path(__file__).resolve().parent

def run(task,repeats):
    d=ROOT/task;mutants=json.loads((d/'mutants.json').read_text()); runs=[]
    variants=[('reference',None),('baseline',None)]+[(m['name'],m) for m in mutants]
    for repeat in range(1,repeats+1):
        for name,mutation in variants:
            with tempfile.TemporaryDirectory(prefix=f'king-{task}-') as temp:
                work=Path(temp);src=work/'src';shutil.copytree(d/('baseline' if name=='baseline' else 'reference')/'src',src);classes=work/'classes';classes.mkdir()
                if mutation:
                    f=src/mutation['file'];s=f.read_text()
                    if mutation['old'] not in s:raise RuntimeError('mutant anchor missing')
                    f.write_text(s.replace(mutation['old'],mutation['new']))
                rc,output=bounded(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-d',str(classes),*[str(f) for f in sorted(src.glob('*.java'))]],work,timeout=30)
                if rc:raise RuntimeError(f'{task} {name} compile: {output}')
                checks=verify(task,classes,work);passed=all(c['pass_'] for c in checks)
                expected=passed if name=='reference' else not passed
                runs.append(dict(repeat=repeat,variant=name,checks=len(checks),passed=sum(c['pass_'] for c in checks),expected_outcome=expected,details=checks))
                print(task,repeat,name,sum(c['pass_'] for c in checks),'/',len(checks),'OK' if expected else 'UNEXPECTED',flush=True)
    hashes={str(f.relative_to(d)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(d.rglob('*.java'))}
    report=dict(task=task,status='runnable_slice',timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),repeats=repeats,all_expected=all(r['expected_outcome'] for r in runs),source_sha256=hashes,runs=runs,limitations=['Public tests and reference; not held out','Local trusted code only, not secure sandbox','No real cluster, broker or production load','No model run or difficulty calibration'])
    (d/'selfcheck-evidence.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--task',choices=[f'K{i:02}' for i in range(1,6)]);p.add_argument('--repeats',type=int,default=3);a=p.parse_args()
    if a.repeats<1:raise SystemExit('repeats must be positive')
    reports=[run(t,a.repeats) for t in ([a.task] if a.task else [f'K{i:02}' for i in range(1,6)])]
    if not a.task:(ROOT/'integration-manifest.json').write_text(json.dumps(dict(all_expected=all(r['all_expected'] for r in reports),tasks=[dict(id=r['task'],repeats=r['repeats'],all_expected=r['all_expected']) for r in reports]),indent=2)+'\n')
    sys.exit(0 if all(r['all_expected'] for r in reports) else 1)

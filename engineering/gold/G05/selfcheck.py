#!/usr/bin/env python3
"""Public development verifier. Timeouts/output limits are NOT a security sandbox."""
import argparse, concurrent.futures, hashlib, json, os, pathlib, signal, subprocess, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parent
LIMIT=131072

def run(command,cwd,timeout):
    with tempfile.TemporaryFile() as log:
        p=subprocess.Popen(command,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        start=time.monotonic(); reason=None
        while p.poll() is None:
            if time.monotonic()-start>timeout: reason='timeout'
            if os.fstat(log.fileno()).st_size>LIMIT: reason='output_limit'
            if reason:
                os.killpg(p.pid,signal.SIGKILL);p.wait();break
            time.sleep(.02)
        log.seek(0);out=log.read(LIMIT).decode(errors='replace')
        return {'exit_code':p.returncode,'failure':reason,'output':out}

def verify(variant,repeat):
    with tempfile.TemporaryDirectory(prefix='g05-clean-') as tmp:
        tmp=pathlib.Path(tmp); classes=tmp/'classes';classes.mkdir()
        groups=[ROOT/'modules/api/src',ROOT/'modules/downstream/src',ROOT/variant/'src',ROOT/'verifier']
        for group in groups:
            sources=sorted(map(str,group.rglob('*.java')))
            result=run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-cp',str(classes),'-d',str(classes),*sources],tmp,30)
            if result['exit_code']!=0:return {'variant':variant,'repeat':repeat,'stage':'compile',**result}
        incident=run(['java','-cp',str(classes),'bench.Incident'],tmp,10)
        result=run(['java','-Xmx96m','-cp',str(classes),'bench.Verify'],tmp,60)
        return {'variant':variant,'repeat':repeat,'stage':'verify','incident':incident,**result}

def semantic_failure(result):
    lines=result.get('output','').splitlines()
    passed=sum(line.startswith('PASS ') for line in lines);failed=sum(line.startswith('FAIL ') for line in lines)
    return (result.get('exit_code')==1 and not result.get('failure')
            and failed>0 and passed+failed==16
            and lines.count(f'SUMMARY passed={passed} failed={failed}')==1
            and not any(line.startswith('ERROR ') for line in lines))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant');parser.add_argument('--candidate',action='store_true');parser.add_argument('--repeats',type=int,default=3);parser.add_argument('--write-evidence',action='store_true');args=parser.parse_args()
    for name,digest in json.loads((ROOT/'fixture-lock.json').read_text()).items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise SystemExit('immutable fixture modified: '+name)
    variants=[args.variant] if args.variant else ['reference','baseline']+['mutants/'+p.name for p in sorted((ROOT/'mutants').iterdir()) if p.is_dir()]
    # One variant at a time; concurrency is only between three isolated clean workspaces.
    results=[]
    for variant in variants:
        if not (ROOT/variant/'src').is_dir():raise SystemExit('missing candidate src directory')
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            batch=list(pool.map(lambda n:verify(variant,n),range(1,args.repeats+1)))
        results.extend(batch)
        print(variant,[(r['repeat'],r['exit_code'],r['failure']) for r in batch],flush=True)
    expected=all(r['stage']=='verify' and r['failure'] is None and r['incident']['exit_code']==0 and not r['incident'].get('failure') and (r['exit_code']==0 if args.candidate or r['variant']=='reference' else semantic_failure(r)) for r in results)
    report={'schema':1,'status':'runnable_slice','public_development_only':True,'repeat_count':args.repeats,'selfcheck_pass':expected,'results':results}
    if args.write_evidence:(ROOT/'verification-results.json').write_text(json.dumps(report,indent=2)+'\n')
    if not expected:raise SystemExit(1)
if __name__=='__main__':main()

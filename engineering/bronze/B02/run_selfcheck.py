#!/usr/bin/env python3
"""Clean temp builds. Trusted development code only; not a secure sandbox."""
import argparse, sys, json, os, pathlib, selectors, shutil, signal, subprocess, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parent

def bounded(command,timeout=30):
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ)
    output=bytearray();deadline=time.monotonic()+timeout
    try:
        while selector.get_map():
            if time.monotonic()>deadline:raise RuntimeError('process timeout')
            for key,_ in selector.select(.1):
                data=os.read(key.fd,4096)
                if not data:selector.unregister(key.fileobj);continue
                output.extend(data)
                if len(output)>65536:raise RuntimeError('output limit')
        return p.wait(timeout=2),output.decode(errors='replace')
    finally:
        selector.close()
        # Reap the whole group even if a failed verifier left its server running.
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.wait()

def evaluate_candidate(package):
    source=package/'src'
    if not source.is_dir() or source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('candidate src must be a directory without symlinks')
    if not list(source.glob('*.java')): raise ValueError('no Java sources')
    with tempfile.TemporaryDirectory(prefix='B02-candidate-') as tmp:
        work=pathlib.Path(tmp);src=work/'src';shutil.copytree(source,src);classes=work/'classes';classes.mkdir()
        code,out=bounded(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-proc:none','-source','21','-target','21','-d',str(classes),*map(str,sorted(src.glob('*.java')))])
        if code:return {'task_id':'B02','passed':False,'status':'build_failed','checks':{},'compile_log':out}
        code,out=bounded([sys.executable,str(ROOT/'verifier/check.py'),str(classes),str(ROOT/'evidence/seed.tsv')])
        checks=json.loads(out)
        passed=code==0 and bool(checks) and all(v=='PASS' for v in checks.values())
        return {'task_id':'B02','passed':passed,'status':'passed' if passed else 'verification_failed','checks':checks,'scope':'trusted local file adapter; not PostgreSQL or a secure sandbox'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=pathlib.Path,help='trusted package directory containing src/')
    args=parser.parse_args()
    if args.candidate:
        try: result=evaluate_candidate(args.candidate.resolve())
        except (ValueError,OSError,RuntimeError,subprocess.TimeoutExpired) as error:
            print(json.dumps({'task_id':'B02','passed':False,'status':'input_or_infrastructure_error','error':str(error)}));return 2
        print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
    report={}
    mutations={
      'wrong_equipment_binding':('!l.equipment().equals(r.equipment()) || ',''),
      'normal_loan_state_omitted':('next.loans.put(l.id(),new Loan(l.id(),l.tenant(),l.equipment(),state));','if(r.damaged()) next.loans.put(l.id(),new Loan(l.id(),l.tenant(),l.equipment(),state));'),
      'conflict_ignored':('if (!previous.loan().equals(r.loan()) || !previous.equipment().equals(r.equipment()) || previous.damaged()!=r.damaged())','if (false)'),
      'partial_commit':('fail(fault,1);','store.commit(next); fail(fault,1);'),
      'damaged_available':('r.damaged()?"REVIEW":"CLEANING"','r.damaged()?"AVAILABLE":"CLEANING"'),
    }
    for variant in ['baseline','reference',*mutations]:
        with tempfile.TemporaryDirectory(prefix='B02-') as tmp:
            work=pathlib.Path(tmp);src=work/'src';shutil.copytree(ROOT/('baseline' if variant=='baseline' else 'reference')/'src',src)
            if variant in mutations:
                file=src/'ReturnService.java';content=file.read_text();old,new=mutations[variant]
                if content.count(old)!=1:raise RuntimeError('mutant target drift')
                file.write_text(content.replace(old,new))
            classes=work/'classes';classes.mkdir()
            code,out=bounded(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-proc:none','-source','21','-target','21','-d',str(classes),*map(str,sorted(src.glob('*.java')))])
            if code:raise RuntimeError('compile failed '+variant+': '+out)
            code,out=bounded(['python3',str(ROOT/'verifier/check.py'),str(classes),str(ROOT/'evidence/seed.tsv')])
            checks=json.loads(out)
            report[variant]={'passed':code==0,'checks':checks}
            if not checks or any(not (v=='PASS' or v.startswith('FAIL: ')) for v in checks.values()):
                raise RuntimeError('infrastructure or malformed result '+variant+': '+out)
            if variant!='reference' and not any(v.startswith('FAIL: ') for v in checks.values()):
                raise RuntimeError('no semantic assertion failure '+variant+': '+out)
            if (variant=='reference')!=(code==0):raise RuntimeError('unexpected outcome '+variant+': '+out)
    print(json.dumps({'task':'B02','scope':'local_file_adapter_not_postgresql','selfcheck':'PASS','variants':report},indent=2,sort_keys=True))
if __name__=='__main__':raise SystemExit(main())

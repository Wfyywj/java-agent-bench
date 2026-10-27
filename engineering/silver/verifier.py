#!/usr/bin/env python3
"""Public independent black-box verifier. Trusted local code only; not a security sandbox."""
import hashlib,json,os,platform,shutil,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
H2_SHA='8dae62d22db8982c3dcb3826edb9c727c5d302063a67eef7d63d82de401f07d3'
H2_PATH=Path(os.environ.get('BENCH_H2_JAR','/tmp/java-agent-bench-h2-2.3.232.jar'))
OUTPUT_LIMIT=131072

def bounded(cmd,cwd,timeout=15):
    # Redirect both streams to bounded monitored files, never unbounded PIPE capture.
    with tempfile.TemporaryDirectory(prefix='silver-output-') as t:
        out=Path(t)/'stdout';err=Path(t)/'stderr'
        with out.open('wb') as o,err.open('wb') as e:
            p=subprocess.Popen(cmd,cwd=cwd,stdout=o,stderr=e,start_new_session=True)
            deadline=time.monotonic()+timeout
            while p.poll() is None:
                if time.monotonic()>deadline or out.stat().st_size+err.stat().st_size>OUTPUT_LIMIT:
                    import signal
                    os.killpg(p.pid,signal.SIGKILL);p.wait()
                    raise RuntimeError('process timeout or output budget exceeded')
                time.sleep(.02)
        stdout=out.read_text(errors='replace');stderr=err.read_text(errors='replace')
        if len(stdout.encode())+len(stderr.encode())>OUTPUT_LIMIT:raise RuntimeError('output budget exceeded')
        if p.returncode:raise RuntimeError(f'exit={p.returncode}: {stderr[:3000]}')
        return stdout.rstrip('\r\n')

def dependencies(tid):
    if tid not in ('S04','S05'):return []
    if not H2_PATH.is_file():raise RuntimeError('Run python engineering/silver/setup_h2.py (explicit dependency download), or set BENCH_H2_JAR')
    if hashlib.sha256(H2_PATH.read_bytes()).hexdigest()!=H2_SHA:raise RuntimeError('H2 checksum mismatch')
    return [str(H2_PATH)]

def compile_variant(task,source,build):
    deps=dependencies(task.name);classes=build/'classes';classes.mkdir()
    if task.name=='S02':
        # Physically separate repository snapshots, compiled independently with explicit edges.
        for module in ('sdk','gateway','service'):
            target=classes/module;target.mkdir()
            prior=[str(classes/x) for x in ('sdk','gateway') if (classes/x).is_dir()]
            cmd=['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-d',str(target)]
            if prior:cmd+=['-classpath',os.pathsep.join(prior)]
            bounded(cmd+[str(p) for p in sorted((source/module/'src').rglob('*.java'))],build,45)
        return os.pathsep.join(str(classes/x) for x in ('sdk','gateway','service'))
    cmd=['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-d',str(classes)]
    if deps:cmd+=['-classpath',os.pathsep.join(deps)]
    bounded(cmd+[str(p) for p in sorted(source.rglob('*.java'))],build,45)
    cp=os.pathsep.join([str(classes)]+deps)
    if task.name=='S05':
        probe=build/'trusted-probe';probe.mkdir()
        bounded(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-cp',cp,'-d',str(probe),str(task/'evaluator/TrustedSearchProbe.java')],build,45)
        cp=os.pathsep.join([str(probe),cp])
    return cp

def verify(task,classpath,work):
    results=[]
    for case in json.loads((task/'fixtures/cases.json').read_text()):
        state=work/case['name'];state.mkdir()
        for f in (task/'fixtures').glob('*.csv'):shutil.copyfile(f,state/f.name)
        traces=[];passed=True
        for step in case['steps']:
            try:
                got=bounded(['java','-Xmx128m','-cp',classpath,'bench.Main',str(state)]+step['args'],work)
                expected=step['expected'];ok=got in expected if isinstance(expected,list) else got==expected
                trace={'args':step['args'],'actual':got,'expected':expected,'passed':ok}
                if task.name=='S05' and step['args'][0]=='search' and 1<=int(step['args'][3])<=1000:
                    observed=bounded(['java','-Xmx128m','-cp',classpath,'evaluation.TrustedSearchProbe',str(state)]+step['args'][1:],work)
                    probe_expected=expected.split('|queries=')[0]+'|observed_executions=1'
                    trace['jdbc_probe']={'actual':observed,'expected':probe_expected,'passed':observed==probe_expected,'counter_owner':'evaluator JDBC proxy, not candidate'}
                    ok=ok and observed==probe_expected
                    trace['passed']=ok
                traces.append(trace)
                if not ok:passed=False;break
            except Exception as exc:
                traces.append({'args':step['args'],'error':str(exc),'passed':False});passed=False;break
        results.append({'name':case['name'],'acceptance':case['acceptance'],'passed':passed,'steps':traces})
    return results

def digest(source):
    h=hashlib.sha256()
    for p in sorted(source.rglob('*.java')):h.update(str(p.relative_to(source)).encode());h.update(p.read_bytes())
    return h.hexdigest()

def selfcheck(task):
    start=time.monotonic();report={'id':task.name,'engine':'H2 2.3.232' if task.name in ('S04','S05') else 'Java 21 CLI + atomic file snapshot' if task.name!='S02' else 'Java 21 separate module classpaths','runtime':bounded(['java','--version'],task),'machine':{'system':platform.system(),'machine':platform.machine(),'python':platform.python_version()},'limits':{'compile_seconds':45,'command_seconds':15,'output_bytes':OUTPUT_LIMIT,'java_heap':'128m'},'visibility':'public development tests, not hidden','sandbox':'trusted local code; not a hostile-code security boundary','variants':{}}
    variants=[('baseline',task/'baseline/src',1),('reference',task/'reference/src',3)]+[(p.name,p/'src',1) for p in sorted((task/'mutants').iterdir())]
    for name,source,repeats in variants:
        item={'source_sha256':digest(source),'compiled':False,'runs':[]};report['variants'][name]=item
        with tempfile.TemporaryDirectory(prefix='silver-clean-') as temp:
            build=Path(temp)
            try:
                cp=compile_variant(task,source,build);item['compiled']=True
                for n in range(repeats):
                    work=build/f'run-{n}';work.mkdir();checks=verify(task,cp,work)
                    item['runs'].append({'passed':sum(x['passed'] for x in checks),'total':len(checks),'checks':checks})
                if name=='reference' and task.name=='S05':
                    diag=build/'diagnostics';diag.mkdir()
                    for f in (task/'fixtures').glob('*.csv'):shutil.copyfile(f,diag/f.name)
                    plan=bounded(['java','-Xmx128m','-cp',cp,'bench.Main',str(diag),'explain'],build)
                    (task/'evidence/h2-explain-measured.txt').write_text(plan+'\n')
                    item['actual_explain_uses_message_index']='IDX_MESSAGES_RECENT' in plan
            except Exception as exc:item['error']=str(exc)
    v=report['variants'];ref=v['reference']
    report['selfcheck_passed']=all(x['compiled'] for x in v.values()) and len(ref['runs'])==3 and all(r['passed']==r['total'] for r in ref['runs']) and all(x['runs'] and any(r['passed']<r['total'] for r in x['runs']) for k,x in v.items() if k!='reference')
    # Race schedule may differ; deterministic acceptance outcomes, not identical race ordering.
    report['three_reference_runs_passed']=len(ref['runs'])==3 and all(r['passed']==r['total'] for r in ref['runs'])
    report['elapsed_seconds']=round(time.monotonic()-start,3)
    (task/'evidence/selfcheck.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    import sys
    reports=[selfcheck(ROOT/tid) for tid in (sys.argv[1:] or ['S01','S02','S03','S04','S05'])]
    print(json.dumps([{'id':r['id'],'passed':r['selfcheck_passed'],'reference_checks':[x['passed'] for x in r['variants']['reference']['runs']],'elapsed_seconds':r['elapsed_seconds']} for r in reports],indent=2))
    raise SystemExit(0 if all(r['selfcheck_passed'] for r in reports) else 1)


def evaluate_candidate(task,candidate):
    """Compile arbitrary trusted candidate source; oracle and fixtures remain evaluator-owned."""
    candidate=Path(candidate).resolve();source=candidate/'src' if (candidate/'src').is_dir() else candidate
    report={'id':task.name,'candidate':str(candidate),'compiled':False,'passed':False,'checks':[],'visibility':'public development tests; not hidden','sandbox':'trusted local code only'}
    try:
        with tempfile.TemporaryDirectory(prefix='silver-candidate-') as temp:
            build=Path(temp);cp=compile_variant(task,source,build);report['compiled']=True
            work=build/'evaluation';work.mkdir();report['checks']=verify(task,cp,work)
            report['passed']=all(c['passed'] for c in report['checks'])
    except Exception as exc:report['error']=str(exc)
    return report

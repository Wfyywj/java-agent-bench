#!/usr/bin/env python3
"""Public engineering slice launcher. Trusted code only; NOT a security sandbox."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, os, platform, re, shutil, signal, subprocess, sys, tempfile, time
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
TIERS={'B':'bronze','S':'silver','G':'gold','D':'diamond','K':'king'}
LIMIT=2*1024*1024
VARIANTS={'S04-spring':'engineering/integration/S04-spring'}

def task_path(task):
    if task in VARIANTS:
        p=ROOT/VARIANTS[task]
        if not p.is_dir():raise ValueError('Integration not implemented')
        return p
    if not re.fullmatch(r'[BSGDK]0[1-5]',task):raise ValueError('Unknown task ID')
    p=ROOT/'engineering'/TIERS[task[0]]/task
    if not p.is_dir():raise ValueError('Task slice not implemented')
    return p

def safe_relative(value):
    p=PurePosixPath(value)
    if not value or p.is_absolute() or any(x in ('..','') for x in p.parts) or '\\' in value:raise ValueError('Unsafe relative path')
    return Path(*p.parts)

def safe_file(root,value):
    rel=safe_relative(value);p=root/rel
    if any((root/Path(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)):raise ValueError('Symlink input rejected')
    if not p.is_file() or not p.resolve().is_relative_to(root.resolve()):raise ValueError('Missing or escaping input')
    return p

def file_hashes(root):
    result={};total_bytes=0
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('Symlink submission rejected')
        if p.is_file():
            total_bytes+=p.stat().st_size
            if p.stat().st_size>5*1024*1024 or total_bytes>50*1024*1024:raise ValueError('Submission file/total too large')
            result[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    if len(result)>2000:raise ValueError('Submission too large')
    return result

def prepare(task,dest):
    taskdir=task_path(task);whitelist=json.loads((taskdir/'agent-files.json').read_text())
    if dest.exists():raise ValueError('Destination must not exist; existing files are never overwritten')
    if dest.resolve().is_relative_to(ROOT.resolve()):raise ValueError('Use a directory outside this repository to keep verifier separate')
    pairs=[]
    for entry in whitelist['files']:
        if isinstance(entry,str):
            source=entry;target=entry.removeprefix('baseline/')
        else:source,target=entry['source'],entry['target']
        src=safe_file(taskdir,source);rel=safe_relative(target)
        if any(x.lower() in ('reference','verifier','mutants','oracle','evidence') for x in Path(source).parts):raise ValueError('Solution-bearing path in agent whitelist')
        pairs.append((src,rel))
    if len({str(r) for _,r in pairs})!=len(pairs):raise ValueError('Duplicate destination')
    dest.mkdir(parents=True)
    for src,rel in pairs:
        out=dest/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,out)
    metadata={'schema_version':'1.0','design_id':task.split('-')[0],'implementation_id':task if task in VARIANTS else task+'-slice','prepared_at':datetime.now(timezone.utc).isoformat(),'source_files':file_hashes(dest),'security':'PUBLIC DEVELOPMENT MATERIAL; NOT AN ISOLATED/HIDDEN EVALUATION'}
    (dest/'PREPARED.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return {'task':task,'workspace':str(dest),'files':len(pairs),'executed':False,'warning':'Reference/verifier remain public in original repository; separation is not a security boundary.'}

def evaluate(task,candidate,output,timeout,trusted):
    if not trusted:raise ValueError('Refusing execution: use --trusted-code only for code you trust. This is NOT a sandbox.')
    taskdir=task_path(task)
    if not candidate.is_dir() or candidate.is_symlink():raise ValueError('Candidate must be a real directory')
    if output and output.resolve().is_relative_to(candidate.resolve()):raise ValueError('Write result outside candidate to preserve submission identity')
    hashes=file_hashes(candidate)
    digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    java_info=subprocess.run(['java','-version'],capture_output=True,text=True,timeout=10)
    environment={'java':java_info.stderr.strip() or java_info.stdout.strip(),'python':sys.version,'platform':platform.platform()}
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,timeout=10)
    dirty=subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True,timeout=10)
    provenance={'git_head':head.stdout.strip() if head.returncode==0 else None,'working_tree_dirty':bool(dirty.stdout.strip()) if dirty.returncode==0 else None,'note':'Official comparisons require a clean checkout at this commit; manifest hash alone does not lock all evaluator code.'}
    start=time.monotonic();reason=None
    cmd=[sys.executable,'-B',str(taskdir/'run_selfcheck.py'),'--candidate',str(candidate.resolve())]
    with tempfile.TemporaryFile() as out:
        p=subprocess.Popen(cmd,cwd=taskdir,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
        while p.poll() is None:
            if time.monotonic()-start>timeout:reason='timeout'
            if os.fstat(out.fileno()).st_size>LIMIT:reason='output_limit'
            if reason:
                os.killpg(p.pid,signal.SIGKILL);p.wait();break
            time.sleep(.05)
        out.seek(0);raw=out.read(LIMIT+1)
        if len(raw)>LIMIT:reason='output_limit';raw=raw[:LIMIT]
    report=None
    try:report=json.loads(raw.decode())
    except (ValueError,UnicodeDecodeError):
        if not reason:reason='invalid_report'
    status=reason or ('passed' if p.returncode==0 else 'failed')
    record={'schema_version':'engineering-1.0','implementation_id':task if task in VARIANTS else task+'-slice','design_id':task.split('-')[0],'dataset':'public-dev-slices','timestamp_utc':datetime.now(timezone.utc).isoformat(),'submission_sha256':digest,'manifest_sha256':hashlib.sha256((taskdir/'task.json').read_bytes()).hexdigest(),'candidate_files':hashes,'environment':environment,'evaluator_provenance':provenance,'elapsed_seconds':round(time.monotonic()-start,3),'status':status,'passed':status=='passed','exit_code':p.returncode,'cost_usd':None,'model':None,'security':'TRUSTED LOCAL CODE ONLY; NOT A SECURITY SANDBOX','report':report,'log':raw.decode(errors='replace')}
    if output:
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    return record

def main():
    ap=argparse.ArgumentParser(description=__doc__);sp=ap.add_subparsers(dest='command',required=True)
    sp.add_parser('list')
    p=sp.add_parser('prepare');p.add_argument('task');p.add_argument('destination',type=Path)
    p=sp.add_parser('evaluate');p.add_argument('task');p.add_argument('candidate',type=Path);p.add_argument('--trusted-code',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--timeout',type=int,default=180)
    a=ap.parse_args()
    try:
        if a.command=='list':result=[{'id':p.name,'implementation_id':p.name+'-slice','tier':p.parent.name,'status':'runnable_slice','candidate_adapter':(p/'agent-files.json').exists()} for tier in TIERS.values() for p in sorted((ROOT/'engineering'/tier).glob('[BSGDK]0[1-5]')) if (p/'task.json').exists()]+ [{'id':name,'implementation_id':name,'tier':'integration','status':'runnable_integration_slice','candidate_adapter':True} for name,path in VARIANTS.items() if (ROOT/path/'task.json').is_file()]
        elif a.command=='prepare':result=prepare(a.task,a.destination)
        else:
            if not 1<=a.timeout<=1800:raise ValueError('Timeout must be 1..1800 seconds')
            result=evaluate(a.task,a.candidate,a.output,a.timeout,a.trusted_code)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if isinstance(result,dict) and result.get('passed') is False else 0
    except (ValueError,OSError,KeyError,json.JSONDecodeError) as e:print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())

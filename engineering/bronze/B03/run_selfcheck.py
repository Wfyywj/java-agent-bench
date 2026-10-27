#!/usr/bin/env python3
"""Local trusted-development harness, NOT a security sandbox."""
import argparse, importlib.util, json, os, shutil, subprocess, tempfile, time, threading
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('check',ROOT/'verifier/check.py');check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
CAP=262144

def bounded(cmd,cwd,timeout=20):
    with tempfile.TemporaryFile() as log:
        p=subprocess.Popen(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        end=time.monotonic()+timeout
        while p.poll() is None:
            if time.monotonic()>end or os.fstat(log.fileno()).st_size>CAP:
                p.kill();p.wait();raise RuntimeError('compile timeout/output bound')
            time.sleep(.02)
        log.seek(0);out=log.read(CAP+1).decode(errors='replace')
        if p.returncode or len(out)>CAP:raise RuntimeError(out[:4000])

MUTANTS={
 'limit_oversized':('PageService.java','limit > 100','limit > 100000'),
 'time_only':('PageService.java','.thenComparing(Box::id)',''),
 'unbound_cursor':('Cursor.java','if (!f[1].equals(tenant) || !f[2].equals(filter) || !f[3].equals(direction))','if (false)'),
 'inclusive_cursor':('PageService.java','sorted.compare(b, after) > 0','sorted.compare(b, after) >= 0'),
 'descending_mismatch':('PageService.java','if (direction.equals("desc")) order = order.reversed();','if (false) order = order.reversed();'),
}

def run(source,mutation=None):
    with tempfile.TemporaryDirectory(prefix='b03-') as tmp:
        tmp=Path(tmp);shutil.copytree(source,tmp/'src');shutil.copy(ROOT/'evidence/warehouse.csv',tmp/'warehouse.csv')
        if mutation:
            filename,old,new=MUTANTS[mutation];p=tmp/'src'/filename;s=p.read_text();assert old in s;p.write_text(s.replace(old,new))
        (tmp/'classes').mkdir()
        bounded(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-encoding','UTF-8','-proc:none','-source','21','-target','21','-d',str(tmp/'classes'),*[str(p) for p in sorted((tmp/'src').glob('*.java'))]],tmp)
        with (tmp/'server.log').open('w+') as log:
            p=subprocess.Popen(['java','-Xmx96m','-cp',str(tmp/'classes'),'Server',str(tmp/'warehouse.csv')],cwd=tmp,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            stop = threading.Event()
            guard_failure = []
            def guard():
                deadline = time.monotonic() + 90
                while not stop.wait(.02):
                    if time.monotonic() > deadline or os.fstat(log.fileno()).st_size > CAP:
                        guard_failure.append("server timeout/output bound")
                        p.kill()
                        return
            watchdog = threading.Thread(target=guard, daemon=True)
            watchdog.start()
            try:
                end=time.monotonic()+10;port=None
                while time.monotonic()<end:
                    log.seek(0);text=log.read(CAP+1)
                    if len(text)>CAP:raise RuntimeError('output bound')
                    if text.startswith('PORT='):port=int(text.splitlines()[0][5:]);break
                    if p.poll() is not None:raise RuntimeError('server stopped: '+text)
                    time.sleep(.03)
                if port is None:raise RuntimeError('server start timeout')
                result=check.verify(port,tmp/'warehouse.csv')
                if guard_failure: raise RuntimeError(guard_failure[0])
                if os.fstat(log.fileno()).st_size>CAP:raise RuntimeError('server output bound')
                return result
            finally:
                stop.set(); watchdog.join(timeout=1)
                p.terminate()
                try:p.wait(timeout=3)
                except subprocess.TimeoutExpired:p.kill();p.wait()

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group();group.add_argument('--candidate',type=Path,help='trusted package directory containing src/');group.add_argument('--candidate-src',type=Path,help='legacy explicit source-directory interface');args=parser.parse_args()
    if args.candidate or args.candidate_src:
        source=args.candidate.resolve()/'src' if args.candidate else args.candidate_src.resolve()
        result=run(source);print(json.dumps(result,sort_keys=True,indent=2));return 0 if all(c['pass'] for c in result.values()) else 1
    results={}
    for name,source,mutant in [('baseline',ROOT/'baseline/src',None),('reference',ROOT/'reference/src',None)]+[(m,ROOT/'reference/src',m) for m in MUTANTS]:
        results[name]=run(source,mutant)
    expected=all(c['pass'] for c in results['reference'].values()) and all(any(not c['pass'] for c in results[n].values()) for n in results if n!='reference')
    print(json.dumps({'task':'B03','selfcheck_pass':expected,'results':results},sort_keys=True,indent=2))
    return 0 if expected else 1
if __name__=='__main__':raise SystemExit(main())

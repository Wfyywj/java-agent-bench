#!/usr/bin/env python3
"""Public development runner. NOT a sandbox for hostile Java."""
import sys,pathlib,tempfile,subprocess,json,hashlib,os,signal,time
ROOT=pathlib.Path(__file__).resolve().parent
def bounded(cmd,cwd,timeout=25):
 with tempfile.TemporaryFile() as out:
  p=subprocess.Popen(cmd,cwd=cwd,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
  deadline=time.monotonic()+timeout
  while p.poll() is None:
   if time.monotonic()>=deadline or os.fstat(out.fileno()).st_size>65536:
    os.killpg(p.pid,signal.SIGKILL);p.wait();raise RuntimeError('process time/output budget exceeded')
   time.sleep(0.02)
  code=p.returncode
  out.seek(0); data=out.read(65537)
  if len(data)>65536: raise RuntimeError('output exceeds 64 KiB; truncated and rejected')
  return code,data.decode(errors='replace')
def run(variant):
 for p,h in json.loads((ROOT/'fixtures.sha256.json').read_text()).items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h: raise RuntimeError('immutable fixture changed: '+p)
 source=(ROOT/variant).resolve(); files=list(source.rglob('*.java'))
 if not files: raise RuntimeError('no Java sources')
 with tempfile.TemporaryDirectory(prefix='gold-check-') as tmp:
  out=pathlib.Path(tmp)/'classes';out.mkdir()
  code,log=bounded(['java','-Xmx192m','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-d',str(out),*[str(f) for f in files],str(ROOT/'verifier/Verify.java')],tmp)
  if code: return {'variant':variant,'phase':'compile','exit':code,'output':log,'passed':False}
  code,log=bounded(['java','-Xmx128m','-cp',str(out),'Verify'],tmp)
  return {'variant':variant,'phase':'verify','exit':code,'output':log,'passed':code==0}
if __name__=='__main__':
 try:
  result=run(sys.argv[1] if len(sys.argv)>1 else 'baseline');print(json.dumps(result,indent=2));sys.exit(0 if result['passed'] else 1)
 except Exception as e: print(json.dumps({'passed':False,'error':str(e)}));sys.exit(2)

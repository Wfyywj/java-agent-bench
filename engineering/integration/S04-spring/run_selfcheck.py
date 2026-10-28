#!/usr/bin/env python3
"""Trusted local candidate evaluator; this is not a sandbox for hostile Java."""
import argparse,hashlib,json,pathlib,subprocess,tempfile,shutil,sys,time,os
R=pathlib.Path(__file__).resolve().parent
ALLOWED={x['target'] for x in json.loads((R/'agent-files.json').read_text())['files'] if x['target'].startswith('src/') and x['target'].endswith('.java')}
def run(cmd,timeout):
 start=time.monotonic()
 try:
  p=subprocess.run(cmd,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
  return {'command':cmd,'exit':p.returncode,'output':p.stdout[:131072],'seconds':round(time.monotonic()-start,3)}
 except subprocess.TimeoutExpired as e:return {'command':cmd,'exit':124,'output':str(e),'seconds':round(time.monotonic()-start,3)}
def evaluate(package):
 package=package.resolve();files={str(p.relative_to(package)) for p in (package/'src').rglob('*') if p.is_file()}
 if files!=ALLOWED: return {'package':str(package),'error':'source whitelist mismatch','missing':sorted(ALLOWED-files),'extra':sorted(files-ALLOWED),'passed':False}
 for p in package.rglob('*'):
  if p.is_symlink():return {'package':str(package),'error':'symlinks forbidden','passed':False}
 digest=hashlib.sha256()
 for f in sorted(files):digest.update(f.encode());digest.update((package/f).read_bytes())
 with tempfile.TemporaryDirectory(prefix='s04-',dir=R) as t:
  t=pathlib.Path(t);sources=[]
  for f in sorted(files):
   p=t/f;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(package/f,p);sources.append(str(p))
  jars=[]
  for dep in json.loads((R/'dependencies.lock.json').read_text()):
   p=pathlib.Path(os.environ.get('S04_SPRING_DEPS','/tmp/java-agent-bench-s04-spring-deps'))/dep['file']
   if hashlib.sha256(p.read_bytes()).hexdigest()!=dep['sha256']:raise ValueError('Dependency hash mismatch: '+str(p))
   jars.append(str(p))
  cp=':'.join(jars);classes=t/'classes';classes.mkdir()
  compile=run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-cp',cp,'-d',str(classes),*sources,*map(str,sorted((R/'regression-tests').rglob('*.java')))],45)
  result={'package':str(package),'source_sha256':digest.hexdigest(),'compile':compile,'passed':False}
  if compile['exit']==0:
   result['test']=run(['java','-Xmx192m','-cp',str(classes)+':'+cp,'bench.IntegrationVerifier'],45)
   result['passed']=(result['test']['exit']==0
       and result['test']['output'].splitlines().count('RESULT tests=20 failed=0')==1
       and sum(line.startswith('PASS ') for line in result['test']['output'].splitlines())==20)
  return result
def semantic_failure(result):
 test=result.get('test',{});lines=test.get('output','').splitlines()
 passed=sum(line.startswith('PASS ') for line in lines);failed=sum(line.startswith('FAIL ') for line in lines)
 return (result.get('compile',{}).get('exit')==0 and test.get('exit')==1
     and not test.get('timeout') and not test.get('failure')
     and failed>0 and passed+failed==20
     and lines.count(f'RESULT tests=20 failed={failed}')==1
     and not any(line.startswith('ERROR ') for line in lines))
p=argparse.ArgumentParser();p.add_argument('--candidate',type=pathlib.Path);a=p.parse_args()
if a.candidate:
 r=evaluate(a.candidate);print(json.dumps(r,indent=2));sys.exit(0 if r['passed'] else 1)
results={'baseline':evaluate(R/'baseline'),'reference':[evaluate(R/'reference') for _ in range(3)],'mutants':{d.name:evaluate(d) for d in sorted((R/'mutants').iterdir())}}
results['passed']=semantic_failure(results['baseline']) and all(r['passed'] for r in results['reference']) and all(semantic_failure(r) for r in results['mutants'].values())
(R/'evidence/selfcheck.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'passed':results['passed'],'baseline':results['baseline']['passed'],'reference':[r['passed'] for r in results['reference']],'mutants':{n:r['passed'] for n,r in results['mutants'].items()}},indent=2));sys.exit(0 if results['passed'] else 1)

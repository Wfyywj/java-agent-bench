#!/usr/bin/env python3
"""Public development verifier; independent Python oracle, bounded trusted subprocesses."""
import argparse,json,subprocess,tempfile,pathlib,time,hashlib,shutil,random
ROOT=pathlib.Path(__file__).resolve().parent
TASK=ROOT.name
class Harness:
 def __init__(self,src,tmp):
  self.src=pathlib.Path(src);self.tmp=pathlib.Path(tmp);self.classes=self.tmp/'classes';self.classes.mkdir();self.state=self.tmp/'state';self.checks=[]
  rc,out=self.proc(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-d',str(self.classes),*map(str,pathlib.Path(src).glob('*.java'))],30)
  assert rc==0,('compile',rc,out)
 def proc(self,cmd,timeout=8):
  import selectors,os,signal
  p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
  selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ);chunks=bytearray();deadline=time.monotonic()+timeout
  try:
   while selector.get_map():
    if time.monotonic()>deadline:raise AssertionError('process timeout')
    for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
     block=os.read(key.fileobj.fileno(),4096)
     if not block:selector.unregister(key.fileobj);continue
     chunks.extend(block)
     if len(chunks)>32768:raise AssertionError('output limit')
   code=p.wait(timeout=max(.01,deadline-time.monotonic()));return code,chunks.decode(errors='replace')
  finally:
   if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
   selector.close();p.stdout.close()
 def call(self,*args,code=0):
  rc,out=self.proc(['java','-Xmx64m','-cp',str(self.classes),'Main',str(self.state),*map(str,args)])
  assert rc==code,(args,rc,out)
  return out.strip()
 def props(self):
  p={};f=self.state/'state.properties'
  if f.exists():
   for l in f.read_text().splitlines():
    if l and not l.startswith('#'):k,v=l.split('=',1);p[k.replace('\\:',':')]=v
  return p
 def check(self,name,cond):
  assert cond,name
  self.checks.append(name)
 def value(self,k,v):self.check(k,self.props().get(k)==str(v))
def d01(h):
 h.call('write','east',0,'a',10);h.call('write','east',0,'b',-3);h.value('east.old.a',10)
 h.call('begin','east');h.value('east.phase','DUAL');h.call('write','east',0,'stale',5,code=2);h.check('fenced-no-mutation','east.entry.stale' not in h.props())
 h.call('cutover','east',code=2);h.check('premature-cutover-rejected',h.props()['east.phase']=='DUAL')
 h.call('backfill','east',1);h.check('checkpoint-durable','east.checkpoint' in h.props())
 h.call('write','east',1,'c',7);h.value('east.new.c',7)
 h.call('backfill','east',1);h.call('backfill','east',1);h.call('cutover','east');h.value('east.epoch',2)
 h.check('legacy-read',h.call('read','east','a')=='10');h.call('write','east',2,'c',7);h.check('stable-identity',len([k for k in h.props() if k.startswith('east.entry.')])==3)
 h.call('write','east',2,'c',8,code=2);h.value('east.new.c',7)
 h.call('write','east',2,'d',11);h.value('east.old.d',11);h.call('rollback','east');h.value('east.epoch',3);h.check('rollback-read',h.call('read','east','d')=='11')
 h.call('pause','east','true');h.call('write','east',3,'e',3,code=2);h.call('write','west',0,'e',3);h.value('west.old.e',3)
 expected={'a':'10','b':'-3','c':'7','d':'11'}
 for kind in ['entry','old','new']:
  actual={k[len('east.'+kind+'.'):]:v for k,v in h.props().items() if k.startswith('east.'+kind+'.')}
  h.check('exact-ledger-'+kind,actual==expected)
 h.check('audit-cutover', 'verified-key-amount' in (h.state/'audit.log').read_text());h.check('audit-rollback','verified-reverse' in (h.state/'audit.log').read_text())
def d02(h):
 # Independent domain model: no Java state transition functions imported or called as oracle.
 model={};used={};history=[]
 def step(op,id='x',slot=None):
  args=[op,id]+([slot] if slot else []);h.call(*args);history.append(args)
  if op=='book':model[id]={'state':'HELD','slot':slot,'paid':0,'refund':0};used[slot]=used.get(slot,0)+1
  elif op=='pay':
   b=model[id];b['paid']=1
   if b['state'] in ('CANCELLED','EXPIRED'):b['refund']=1
   elif b['state']=='HELD':b['state']='CONFIRMED'
  elif op in ('cancel','expire'):
   b=model[id]
   if b['state'] in ('HELD','CONFIRMED'):used[b['slot']]-=1;b['state']='CANCELLED' if op=='cancel' else 'EXPIRED';b['refund']=b['paid']
  elif op=='move':b=model[id];used[b['slot']]-=1;used[slot]=used.get(slot,0)+1;b['slot']=slot
  p=h.props()
  for k,b in model.items():
   for field,v in b.items():h.check(f'{len(history)}:{k}:{field}',p.get(f'b.{k}.{field}','0')==str(v))
  for slot,v in used.items():h.check(f'{len(history)}:capacity:{slot}',p.get('used.'+slot,'0')==str(v))
 step('book','a','s1');step('cancel','a');step('pay','a');step('pay','a')
 step('book','b','s1');step('pay','b');step('move','b','s2');step('expire','b');step('pay','b')
 # Fixed seed legal histories, including both event orders and durable process restarts.
 rng=random.Random(2102)
 for i in range(6):
  id='r'+str(i);step('book',id,'s'+str(i+3))
  ops=['pay','cancel'];rng.shuffle(ops)
  for op in ops:step(op,id)
 h.check('projection-not-premature','b.a.projection' not in h.props());h.call('tick');h.value('b.a.projection','CANCELLED');h.value('b.b.projection','EXPIRED')
 # Capacity rejection and invalid transition leave durable state unchanged.
 h.call('book','cap1','full');h.call('book','cap2','full');before=h.props();h.call('book','cap3','full',code=2);h.check('capacity-rejection-atomic',before==h.props());h.call('move','a','s7',code=2);h.check('terminal-move-rejected',before==h.props())
 return {'seed':2102,'history':history,'projection_bound':'one explicit tick; not linearized with commands'}
def d03(h):
 h.call('seed');h.value('hit.percent',98);h.value('backlog',6)
 h.call('apply','ineligible','false',code=2);h.check('eligibility-not-cache', 'accepted.ineligible' not in h.props())
 h.call('apply','a','true');h.call('apply','a','true');h.value('quota',1)
 h.call('project','a',3);h.call('project','a',1);h.value('projection.a',3)
 before=h.props();h.call('recover','east',2,'apply',code=2);h.check('lock-stop-no-mutation',before==h.props())
 h.call('intervene','limit-workers');h.value('locks',1);h.value('backlog',6)
 before=h.props();h.call('recover','east',2,'dry-run');h.check('dry-run-no-mutation',before==h.props());h.call('recover','all',2,'apply',code=2);h.call('recover','east',3,'apply',code=2);h.check('scope-budget-no-mutation',before==h.props())
 h.call('recover','east',2,'apply');h.value('backlog',4);h.value('checkpoint',2);h.value('l1.version',2);h.value('l2.version',2)
 h.call('recover','east',2,'apply');h.value('backlog',2);h.value('checkpoint',4)
 h.check('simulation-labeled','simulation=true' in h.call('metrics'));h.check('evidence-preserved',(h.state/'audit.log').read_text().startswith('seed\n'))
 # Fixed clock offsets independently normalize the raw event fixture.
 events=json.loads((ROOT/'baseline/artifacts/events.json').read_text());normalized=sorted((e['local']-e['offset'],e['event']) for e in events)
 h.check('clock-normalized-order',[e[1] for e in normalized]==['deploy','cache-stale','lock-wait','backlog'])
 return {'timeline':normalized,'experiments':{'limit-workers':'locks 8 -> 1; backlog remains 6 until bounded drain','cache-hit-hypothesis':'98% hit does not establish eligibility freshness'},'unsupported':['real production latency','actual CPU or database lock measurements']}
def d04(h):
 def manifest(name,dep='builtin-expression@1#original-2026',perm='compute',fmt='expression-v1'):
  f=h.tmp/(name+'.properties');f.write_text(f'dependency={dep}\npermissions={perm}\nformat={fmt}\n');return f
 h.call('review',manifest('safe'),'a');h.value('approved.a','true')
 for i,dep in enumerate(['unknown@1','builtin-expression@2','http://untrusted']):
  h.call('review',manifest('dep'+str(i),dep),'bad'+str(i),code=2);h.check('forbidden-dependency-'+str(i),'approved.bad'+str(i) not in h.props())
 for i,perm in enumerate(['network','filesystem','compute,network']):
  h.call('review',manifest('perm'+str(i),perm=perm),'p'+str(i),code=2);h.check('forbidden-permission-'+str(i),'approved.p'+str(i) not in h.props())
 h.call('review',manifest('legacy',fmt='serialized-java'),'old',code=2);h.check('legacy-rejected','approved.old' not in h.props())
 h.call('execute','missing',1,'1+2',code=2);h.check('unapproved-no-result','result.missing' not in h.props())
 h.call('execute','a',1001,'1+2',code=2);h.check('cpu-budget','result.a' not in h.props())
 h.call('execute','a',1,'1'*129,code=2);h.check('input-budget','result.a' not in h.props())
 h.call('execute','a',1,'http://host',code=2);h.check('no-network-language','result.a' not in h.props())
 h.call('marker',code=2);h.check('harmless-boundary-proof',not (h.state/'harmless-marker').exists())
 h.check('good-tenant-after-bad',h.call('execute','a',1,'17+24')=='41');h.value('result.a',41)
 audit=(h.state/'audit.log').read_text();h.check('sensitive-input-not-audited','17+24' not in audit);h.check('dependency-provenance-audited','original-2026' in audit)
def d05(h):
 h.call('init','cycle7-snapshot3');h.value('snapshot','cycle7-snapshot3');h.call('init','changed',code=2);h.value('members','a,b,poison,c,d')
 h.call('step',1,'crash',code=77);h.value('provider.cycle7-snapshot3:a',1);h.value('unknown.a','true');h.check('checkpoint-not-ahead',h.props().get('cursor','0')=='0')
 h.call('lease');h.value('epoch',2);before=h.props();h.call('step',1,'normal',code=2);h.check('stale-worker-no-write',before==h.props())
 h.call('step',2,'normal');h.value('provider.cycle7-snapshot3:a',1);h.value('result.a','issued');h.value('cursor',1);h.check('unknown-resolved','unknown.a' not in h.props())
 h.call('step',2,'normal');h.value('cursor',2);h.call('step',2,'normal');h.value('quarantine.poison','invalid');h.value('cursor',3)
 h.call('step',2,'crash',code=77);h.value('unknown.c','true');h.call('cancel');before=h.props();h.call('step',2,'normal',code=2);h.check('cancel-stops-new-work',before==h.props());h.check('cancel-not-atomic-revoke',h.props()['result.a']=='issued');h.check('cancel-unknown-preserved',h.props()['unknown.c']=='true');h.check('cancel-unissued-explicitly-derivable','provider.cycle7-snapshot3:d' not in h.props())
 h.check('no-duplicate-provider-effects',all(v=='1' for k,v in h.props().items() if k.startswith('provider.')))
 return {'issued':['a','b'],'unknown':['c'],'not_issued':['d'],'quarantined':['poison'],'snapshot':h.props()['snapshot']}
def evaluate(src):
 with tempfile.TemporaryDirectory(prefix=TASK+'-') as tmp:
  h=None
  try:
   h=Harness(src,tmp);details=globals()[TASK.lower()](h);return {'pass':True,'checks':h.checks,'details':details,'state':h.props(),'audit':(h.state/'audit.log').read_text()}
  except Exception as e:return {'pass':False,'checks':h.checks if h else [],'failure':str(e)}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--candidate');ap.add_argument('--selfcheck',action='store_true');args=ap.parse_args()
 if args.candidate:
  result=evaluate(ROOT/args.candidate);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['pass'] else 1
 rows=[]
 for repeat in range(3):
  for label,src in [('reference',ROOT/'reference/src'),('baseline',ROOT/'baseline/src')]+[(d.name,d) for d in sorted((ROOT/'mutants').iterdir())]:
   start=time.monotonic();r=evaluate(src);r.update(label=label,repeat=repeat+1,elapsed_seconds=round(time.monotonic()-start,3));rows.append(r)
   print(TASK,repeat+1,label,'PASS' if r['pass'] else 'FAIL',len(r['checks']),flush=True)
 report={'task':TASK,'status':'runnable_slice','java':'21','public_development_only':True,'results':rows,'selfcheck_pass':all(r['pass']==(r['label']=='reference') for r in rows)}
 (ROOT/'evidence/selfcheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['selfcheck_pass'] else 1
if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Evaluate agent-authored operation histories against reference and known faulty systems.
Oracle is a declarative fold over events, not the implementation. Shrinking only keeps legal histories.
Public dev matrix, no hidden holdout or claims of complete interleaving coverage.
"""
import sys,json,tempfile,pathlib,importlib.util,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runner',ROOT/'run.py');run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
def expected(history):
 b={};cap={}
 for row in history:
  op,id,*tail=row
  if op=='book':
   if id in b or len(tail)!=1 or cap.get(tail[0],0)>=2:return None
   b[id]=dict(state='HELD',slot=tail[0],paid=0,refund=0);cap[tail[0]]=cap.get(tail[0],0)+1
  else:
   if id not in b:return None
   x=b[id]
   if op=='pay':
    x['paid']=1
    if x['state'] in ('CANCELLED','EXPIRED'):x['refund']=1
    else:x['state']='CONFIRMED'
   elif op in ('cancel','expire'):
    if x['state'] in ('HELD','CONFIRMED'):cap[x['slot']]-=1;x['state']='CANCELLED' if op=='cancel' else 'EXPIRED';x['refund']=x['paid']
   elif op=='move':
    if x['state'] not in ('HELD','CONFIRMED') or len(tail)!=1 or cap.get(tail[0],0)>=2:return None
    cap[x['slot']]-=1;x['slot']=tail[0];cap[tail[0]]=cap.get(tail[0],0)+1
   else:return None
 result={f'b.{id}.{k}':str(v) for id,x in b.items() for k,v in x.items()};result.update({'used.'+s:str(v) for s,v in cap.items()});return result

def mismatch(h,history):
 model=expected(history)
 if model is None:return False
 shutil.rmtree(h.state,ignore_errors=True)
 for row in history:
  try:h.call(*row)
  except AssertionError:return True
 p=h.props();return any(p.get(k,'0')!=v for k,v in model.items())
def shrink(h,history):
 result=history[:];changed=True
 while changed:
  changed=False
  for i in range(len(result)):
   candidate=result[:i]+result[i+1:]
   if candidate and expected(candidate) is not None and mismatch(h,candidate):result=candidate;changed=True;break
 return result

def main():
 histories=json.load(open(sys.argv[1] if len(sys.argv)>1 else ROOT/'reference/artifacts/suite.json'))
 assert isinstance(histories,list) and 1<=len(histories)<=100
 assert all(1<=len(h)<=100 and expected(h) is not None for h in histories),'invalid history: shrinker/test inputs must preserve creation and capacity preconditions'
 rows=[]
 for label,source in [('reference',ROOT/'reference/src')]+[(p.name,p) for p in sorted((ROOT/'mutants').iterdir())]:
  with tempfile.TemporaryDirectory() as tmp:
   h=run.Harness(source,tmp);detected=[mismatch(h,x) for x in histories];minima=[shrink(h,x) if hit else None for x,hit in zip(histories,detected)]
   rows.append({'system':label,'detected_by_history':detected,'minimal_legal_histories':minima})
 report={'matrix':rows,'reference_clean':not any(rows[0]['detected_by_history']),'mutants_killed':sum(any(r['detected_by_history']) for r in rows[1:]),'mutants_total':len(rows)-1,'shrinking':'deletion-1-minimal under legal preconditions; not global minimum','public_development':True}
 print(json.dumps(report,indent=2));return 0 if report['reference_clean'] and report['mutants_killed']==report['mutants_total'] else 1
if __name__=='__main__':raise SystemExit(main())

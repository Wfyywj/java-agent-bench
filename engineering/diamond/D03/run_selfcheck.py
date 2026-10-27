#!/usr/bin/env python3
import argparse,pathlib,json,run
p=argparse.ArgumentParser();p.add_argument('--candidate');a=p.parse_args()
if a.candidate:
 root=pathlib.Path(a.candidate).resolve();src=root/'src' if (root/'src').is_dir() else root
 r=run.evaluate(src)
 artifact=(root/'artifacts/diagnosis.json') if (root/'src').is_dir() else root.parent/'artifacts/diagnosis.json'
 try:
  diagnosis=json.loads(artifact.read_text())
  checks={'simulation_labeled':diagnosis.get('simulation') is True,'clock_evidence':diagnosis.get('normalized_timeline')==[{'event':'deploy','time':10},{'event':'cache-stale','time':12},{'event':'lock-wait','time':15},{'event':'backlog','time':20}],'competing_hypotheses':{x.get('id') for x in diagnosis.get('hypotheses',[])}=={'freshness','lock-amplification'},'bounded_scope':diagnosis.get('recovery',{}).get('tenant')=='east' and diagnosis.get('recovery',{}).get('max_batch')==2 and diagnosis.get('recovery',{}).get('dry_run') is True and diagnosis.get('recovery',{}).get('stop_if_locks_above')==2,'unsupported_claims':set(diagnosis.get('unsupported',[]))=={'production causality','real performance'}}
  r['diagnosis_checks']=checks;r['pass']=r['pass'] and all(checks.values())
 except Exception as e:r['pass']=False;r['diagnosis_failure']=str(e)
 print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(0 if r['pass'] else 1)
raise SystemExit(run.main())

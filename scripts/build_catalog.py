"""Build website data from canonical manifests. No network or model calls.

Design ``status`` stays ``design_only``. Optional ``slice_implementation`` may
point at a gates_green runnable slice; ``full_catalog_ready`` on that pointer
must be false. It does not mark the original design ready.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SUMMARY_REL='engineering/m1-gates/evidence/summary.json'

def validate_design(task):
 if task.get('status')!='design_only':
  raise AssertionError('catalog status must stay design_only')
 if task.get('full_catalog_ready') is True:
  raise AssertionError('catalog design must not claim full_catalog_ready')
 link=task.get('slice_implementation')
 if link is None:return
 if not isinstance(link,dict):
  raise AssertionError('slice_implementation must be an object')
 if link.get('engineering_status')!='gates_green':
  raise AssertionError('slice engineering_status must be gates_green, not a readiness marker')
 if link.get('full_catalog_ready') is not False:
  raise AssertionError('slice_implementation.full_catalog_ready must be false')
 impls=link.get('implementations')
 if not isinstance(impls,list) or not impls or not all(isinstance(item,str) and item for item in impls):
  raise AssertionError('slice_implementation.implementations must name slices')
 if link.get('evidence')!=SUMMARY_REL:
  raise AssertionError('slice evidence must point at the M1 summary')
 extra=set(link)-{'engineering_status','full_catalog_ready','implementations','evidence'}
 if extra:
  raise AssertionError('unexpected slice_implementation fields: '+','.join(sorted(extra)))

def main():
 tasks=json.loads((ROOT/'catalog/tasks.json').read_text())
 assert len({t['id'] for t in tasks})==len(tasks)
 for t in tasks:
  validate_design(t)
  assert len(t['acceptance'])>=5
  assert sum(r['weight'] for r in t['rubric'])==100
 (ROOT/'dist/tasks.json').write_text(json.dumps(tasks,ensure_ascii=False,indent=2)+'\n')
 runnable=json.loads((ROOT/'dist/runnable.json').read_text())
 for t in runnable:
  m=json.loads((ROOT/'tasks'/t['id']/'task.json').read_text())
  t['acceptance']=m['check_names'];t['risks']=m['limitations'];t['environment']['task_version']=m['version']
  assert len(t['acceptance'])==m['test_count']
 (ROOT/'dist/runnable.json').write_text(json.dumps(runnable,ensure_ascii=False,indent=2)+'\n')
 print(f'Validated and built {len(tasks)} design tasks, {len(runnable)} runnable mechanism tasks.')

if __name__=='__main__':
 main()

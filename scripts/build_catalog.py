"""Build website data from canonical manifests. No network or model calls."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
tasks=json.loads((ROOT/'catalog/tasks.json').read_text())
assert len({t['id'] for t in tasks})==len(tasks)
for t in tasks:
 assert t['status']=='design_only'
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

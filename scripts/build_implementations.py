"""Generate discovery metadata; never promotes the full design to ready."""
import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAT={t['id']:t for t in json.loads((ROOT/'catalog/tasks.json').read_text())}
records=[]
for tier in ['bronze','silver','gold','diamond','king']:
 for p in sorted((ROOT/'engineering'/tier).glob('[BSGDK]0[1-5]')):
  if not (p/'task.json').exists() or not (p/'agent-files.json').exists():continue
  m=json.loads((p/'task.json').read_text());id=p.name
  scope=m.get('implemented_scope') or m.get('scope') or m.get('limitations') or m.get('implementedScope') or '以本题 task.json 与 README 标明的范围和局限为准。'
  if not isinstance(scope,str):scope=json.dumps(scope,ensure_ascii=False,indent=2)
  records.append({'id':id,'implementation_id':id+'-slice','tier':tier,'status':'runnable_slice','manifest_sha256':hashlib.sha256((p/'task.json').read_bytes()).hexdigest(),'path':str(p.relative_to(ROOT)),'scope':scope,'command':f'python3 scripts/engineering.py prepare {id} /tmp/{id.lower()}-work\n# 仅在你确认代码可信后执行；正式模型提交需另建隔离环境\npython3 scripts/engineering.py evaluate {id} /tmp/{id.lower()}-work --trusted-code --output /tmp/{id.lower()}-result.json','model_evaluated':False,'security':'not_a_secure_sandbox'})
p=ROOT/'engineering/integration/S04-spring'
if (p/'task.json').is_file() and (p/'agent-files.json').is_file():
 m=json.loads((p/'task.json').read_text())
 records.insert(0,{'id':'S04','implementation_id':'S04-spring','tier':'silver','status':'runnable_integration_slice','manifest_sha256':hashlib.sha256((p/'task.json').read_bytes()).hexdigest(),'path':str(p.relative_to(ROOT)),'scope':'真实 Spring 事务代理 + JDBC/H2；不是 PostgreSQL、HTTP 认证或完整生产连接池验证。详见本题覆盖边界。','command':'python3 engineering/integration/S04-spring/tools/bootstrap.py\npython3 scripts/engineering.py prepare S04-spring /tmp/s04-spring-work\npython3 scripts/engineering.py evaluate S04-spring /tmp/s04-spring-work --trusted-code --output /tmp/s04-spring-result.json','model_evaluated':False,'security':'not_a_secure_sandbox'})
(ROOT/'catalog/implementations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
(ROOT/'dist/implementations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print(f'{len(records)} candidate-adapter slices discovered; original catalog statuses unchanged.')

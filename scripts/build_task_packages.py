"""Build deterministic public participant ZIPs, never grading assets."""
from pathlib import Path
import importlib.util,json,tempfile,zipfile
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('launcher',ROOT/'scripts/engineering.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=ROOT/'dist/packages';out.mkdir(parents=True,exist_ok=True)
records=json.loads((ROOT/'catalog/implementations.json').read_text())
for rec in records:
 task=rec['implementation_id'].removesuffix('-slice')
 with tempfile.TemporaryDirectory(prefix='jab-package-') as tmp:
  candidate=Path(tmp)/'candidate';m.prepare(task,candidate)
  meta=json.loads((candidate/'PREPARED.json').read_text());meta.pop('prepared_at',None);meta['manifest_sha256']=rec['manifest_sha256'];(candidate/'PREPARED.json').write_text(json.dumps(meta,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
  (candidate/'EVALUATION_NOTICE.txt').write_text('公开开发题。该包不包含评分器或参考答案，但它们在公开仓库可见。不得声称隐藏评测或无污染。正式模型执行需要另建隔离环境。请阅读 PROMPT.md 或本题说明；评估入口见 https://github.com/Wfyywj/java-agent-bench 。\n',encoding='utf-8')
  with zipfile.ZipFile(out/(rec['implementation_id']+'.zip'),'w',compression=zipfile.ZIP_DEFLATED) as z:
   for p in sorted(candidate.rglob('*')):
    if p.is_file():
     rel=str(p.relative_to(candidate));info=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,p.read_bytes())
print(f'Built {len(records)} participant ZIPs without grading code.')

import json,pathlib,run
root=pathlib.Path(__file__).resolve().parent
def semantic_failure(result):
 lines=result.get('output','').splitlines()
 passed=sum(line.startswith('PASS ') for line in lines);failed=sum(line.startswith('FAIL ') for line in lines)
 return (result.get('phase')=='verify' and result.get('exit')==1
     and failed>0 and lines.count(f'INVARIANTS={passed+failed} FAILURES={failed}')==1
     and not result.get('failure') and not result.get('timeout')
     and not any(line.startswith('ERROR ') for line in lines))
variants=json.loads((root/'task.json').read_text())['variants'];results=[]
for repeat in range(3):
 for v in variants:
  r=run.run(v);r['repeat']=repeat+1;results.append(r)
passed=all(r['phase']=='verify' and (r['passed'] if r['variant']=='reference' else semantic_failure(r)) for r in results)
report={'selfcheck_passed':passed,'repeats':3,'results':results}
(root/'verification-results.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'selfcheck_passed':passed,'runs':len(results),'reference_passes':sum(r['passed'] for r in results)}))
raise SystemExit(0 if passed else 1)

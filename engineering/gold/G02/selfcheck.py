import json,pathlib,run
root=pathlib.Path(__file__).resolve().parent
variants=json.loads((root/'task.json').read_text())['variants'];results=[]
for repeat in range(3):
 for v in variants:
  r=run.run(v);r['repeat']=repeat+1;results.append(r)
passed=all(r['passed']==(r['variant']=='reference') and r['phase']=='verify' for r in results)
report={'selfcheck_passed':passed,'repeats':3,'results':results}
(root/'verification-results.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'selfcheck_passed':passed,'runs':len(results),'reference_passes':sum(r['passed'] for r in results)}))
raise SystemExit(0 if passed else 1)

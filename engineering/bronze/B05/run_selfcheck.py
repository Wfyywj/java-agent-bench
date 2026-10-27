#!/usr/bin/env python3
"""Trusted public fixture runner; NOT a sandbox or a model evaluation."""
import json,sys,tempfile,shutil,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[2]/'harness'))
from bench import command

def run(name,source,mutation=None):
    with tempfile.TemporaryDirectory(prefix='b05-') as td:
        td=Path(td);src=td/'src';shutil.copytree(source,src);classes=td/'classes';classes.mkdir();data=td/'data';data.mkdir()
        if mutation:
            filename,before,after=mutation;p=src/filename;s=p.read_text();assert before in s;s=s.replace(before,after,1);p.write_text(s)
        files=sorted(str(p) for p in src.glob('*.java'))+[str(ROOT/'verifier/Verify.java')]
        build=command(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-encoding','UTF-8','-proc:none','-d',str(classes),*files],td,30,65536)
        if build['exit_code']!=0: raise RuntimeError(build)
        result=command(['java','-Xmx96m','-cp',str(classes),'Verify',str(data)],td,15,65536)
        if result['timed_out'] or result['output_limited']: raise RuntimeError(result)
        lines=result['stdout'].splitlines(); assert len(lines)==28,(name,lines)
        return {'variant':name,'compiled':True,'exit_code':result['exit_code'],'passed':sum(s.startswith('PASS ') for s in lines),'failed':[s[5:] for s in lines if s.startswith('FAIL ')],'checks':lines}

def diagnosis_ok(path):
    expected=json.loads((ROOT/'verifier/diagnosis-contract.json').read_text())
    try: actual=json.loads(Path(path).read_text())
    except (OSError,ValueError): return False
    return all(actual.get(k)==v for k,v in expected.items())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,help='trusted package directory containing src/ and diagnosis.json')
    args=parser.parse_args()
    if args.candidate:
        candidate=args.candidate.resolve()
        result=run('candidate',candidate/'src')
        result['diagnosis_contract_pass']=diagnosis_ok(candidate/'diagnosis.json')
        result['task_pass']=result['exit_code']==0 and result['passed']==28 and not result['failed'] and result['diagnosis_contract_pass']
        print(json.dumps(result,indent=2));return 0 if result['task_pass'] else 1
    variants=[('baseline',ROOT/'baseline/src',None),('reference',ROOT/'reference/src',None),
      ('mutant_corrupted_output',ROOT/'reference/src',('StagingFile.java','writer.write(Csv.encode(id)+","+Csv.encode(name)+","+Csv.encode(email));','writer.write("CORRUPTED");')),
      ('mutant_missing_header',ROOT/'reference/src',('Importer.java','stage.header();','/* header omitted */')),
      ('mutant_input_leak',ROOT/'reference/src',('Importer.java','try (BufferedReader reader=new BufferedReader(new InputStreamReader(input,StandardCharsets.UTF_8));\n       StagingFile stage=new StagingFile(target)) {','BufferedReader reader=new BufferedReader(new InputStreamReader(input,StandardCharsets.UTF_8));\n  try (StagingFile stage=new StagingFile(target)) {')),
      ('mutant_temp_leak',ROOT/'reference/src',('StagingFile.java','finally { Files.deleteIfExists(temp); }','finally { /* cleanup omitted */ }')),
      ('mutant_raw_error',ROOT/'reference/src',('Importer.java','new Result("CSV_FIELDS",line,0)','new Result("CSV_FIELDS:"+raw,line,0)'))]
    results=[run(*v) for v in variants]
    diag=diagnosis_ok(ROOT/'reference/diagnosis.json')
    negative_diag=not diagnosis_ok(ROOT/'baseline/diagnosis.json')
    ok=results[1]['exit_code']==0 and results[1]['passed']==28 and all(x['exit_code']==1 and x['failed'] for i,x in enumerate(results) if i!=1) and diag and negative_diag
    payload={'task_id':'B05','schema_version':1,'selfcheck_pass':ok,'diagnosis_contract_pass':diag,'incorrect_baseline_diagnosis_rejected':negative_diag,'checks_per_variant':28,'results':results,'scope':'Public development fixture; no model scores; trusted code only, not a sandbox.'}
    print(json.dumps(payload,indent=2));return 0 if ok else 1
if __name__=='__main__':sys.exit(main())

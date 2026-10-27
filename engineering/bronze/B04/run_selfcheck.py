#!/usr/bin/env python3
"""Compile trusted local fixtures in fresh temp dirs; bounded subprocesses, NOT a sandbox."""
import argparse, json, os, resource, shutil, signal, subprocess, tempfile
from pathlib import Path
from verifier.check import ROOT, cases, verify_review

def bounded(cmd, cwd, data=''):
    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE, (65536,65536))
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.PIPE, stdout=out, stderr=err,
            start_new_session=True, preexec_fn=limits, env={**os.environ,'LC_ALL':'C','TZ':'UTC'})
        try: proc.communicate(data.encode(), timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL); proc.communicate(); raise AssertionError('timeout '+cmd[0])
        out.seek(0); err.seek(0)
        stdout, stderr = out.read(65537).decode(), err.read(65537).decode()
        assert len(stdout.encode()) <= 65536 and len(stderr.encode()) <= 65536, 'output bound'
        assert proc.returncode == 0, (cmd,proc.returncode,stderr)
        return stdout,stderr

def exercise(source, mutation=None):
    with tempfile.TemporaryDirectory(prefix='B04-') as tmp:
        tmp=Path(tmp); shutil.copytree(source,tmp/'src'); (tmp/'classes').mkdir()
        if mutation:
            filename, old, new = mutation
            file=tmp/'src'/filename; text=file.read_text(); assert old in text
            file.write_text(text.replace(old,new))
        bounded(['java','-Xmx128m','-m','jdk.compiler/com.sun.tools.javac.Main','-proc:none','-source','21','-target','21','-encoding','UTF-8','-d',str(tmp/'classes'),*map(str,sorted((tmp/'src').glob('*.java')))],tmp)
        tests=cases()
        data=''.join(','.join(x['prices'])+'\t'+x['discount']+'\t'+x['tax']+'\tNOTE_SECRET_'+x['id']+'\n' for x in tests)
        stdout,stderr=bounded(['java','-Xmx96m','-cp',str(tmp/'classes'),'QuoteCli'],tmp,data)
        lines=stdout.splitlines(); assert len(lines)==len(tests), 'response count'
        failures=[x['id'] for x,line in zip(tests,lines) if line!=x['expected']]
        if 'NOTE_SECRET_' in stderr: failures.append('note-log')
        return failures,dict(zip((x['id'] for x in tests),lines)),stderr

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,help='review package directory containing review.json; no source repair is evaluated')
    args=parser.parse_args()
    if args.candidate:
        package=args.candidate.resolve()
        try:
            if not package.is_dir(): raise ValueError('candidate package directory required')
            failures=verify_review(package/'review.json')
        except (ValueError,OSError,KeyError,TypeError) as error:
            print(json.dumps({'task_id':'B04','passed':False,'status':'invalid_input','error':str(error)}));return 2
        print(json.dumps({'task_id':'B04','passed':not failures,'status':'passed' if not failures else 'verification_failed','failures':failures,'scope':'structured review anchors only; no candidate code repair or prose scoring; public trusted fixture'},indent=2))
        return 1 if failures else 0
    result={'task':'B04','cases':len(cases()),'secure_sandbox':False}
    baseline, observed, log=exercise(ROOT/'baseline/src')
    assert {'decimal-half','tax-location','legacy-null','note-log'} <= set(baseline), baseline
    # Verify every frozen blocking verdict against actual candidate observations.
    for finding in json.loads((ROOT/'verifier/verdict-fixture.json').read_text())['findings']:
        filename, symbol = finding['location'].split(':',1)
        assert symbol in (ROOT/'baseline/src'/filename).read_text(), finding['location']
        if finding['id']=='note-log': assert 'NOTE_SECRET_invalid-discount' in log
        else: assert observed[finding['case']]==finding['observed'], finding
    assert all(observed[x]=='ERROR\t422\tINVALID_QUOTE' for x in ['overflow','invalid-discount','negative-discount'])
    result['baseline']={'expected_failure':True,'failed_cases':baseline,'review_rejected':bool(verify_review(ROOT/'baseline/review.json'))}
    assert result['baseline']['review_rejected']
    correct,_,_=exercise(ROOT/'reference/src'); assert not correct,correct
    assert not verify_review(ROOT/'reference/review.json')
    result['reference']={'passed':True,'failed_cases':[],'review_accepted':True}
    mutants={
        'round-down':('QuoteCalculator.java','RoundingMode.HALF_UP','RoundingMode.DOWN'),
        'null-discount':('QuoteCalculator.java','quote.discount() == null ? BigDecimal.ZERO : quote.discount()','quote.discount()'),
        'log-note':('AuditLog.java','"quote_rejected code=INVALID_QUOTE"','"quote_rejected " + quote.note()'),
        'omit-tax':('QuoteCalculator.java','subtotal.add(tax)','subtotal')}
    result['mutants']={}
    for name, mutation in mutants.items():
        failures,_,_=exercise(ROOT/'reference/src',mutation); assert failures,name+' survived'
        result['mutants'][name]={'killed':True,'failed_cases':failures}
    with tempfile.TemporaryDirectory() as temp:
        review=json.loads((ROOT/'reference/review.json').read_text())
        review['findings'].append(dict(id='overflow-is-bug',kind='money_precision',severity='blocking'))
        path=Path(temp)/'review.json';path.write_text(json.dumps(review))
        assert verify_review(path)
    result['review_false_positive_mutant_rejected']=True
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__=='__main__': raise SystemExit(main())

#!/usr/bin/env python3
"""Trusted-code development harness, not a sandbox. Temp builds; bounded subprocesses."""
import argparse,json,pathlib,shutil,subprocess,tempfile,time,os
ROOT=pathlib.Path(__file__).resolve().parent

def run(cmd,cwd,timeout=25):
    with tempfile.TemporaryFile() as output:
        p=subprocess.Popen(cmd,cwd=cwd,stdout=output,stderr=subprocess.STDOUT,env=dict(os.environ,TZ='UTC'))
        deadline=time.monotonic()+timeout
        while p.poll() is None:
            if time.monotonic()>deadline or os.fstat(output.fileno()).st_size>131072:
                p.kill();p.wait();raise RuntimeError('timeout/output budget exceeded')
            time.sleep(.02)
        output.seek(0);text=output.read(131073).decode(errors='replace')
        if len(text)>131072:raise RuntimeError('output budget exceeded')
        return p.returncode,text

def verify(candidate):
    contract=json.loads((ROOT/'verifier/stakeholder-contract.json').read_text())
    decisions=json.loads((candidate/'decisions.json').read_text())
    decision_ok=all(decisions.get(k)==v for k,v in contract.items())
    with tempfile.TemporaryDirectory(prefix='b01-') as temp:
        tmp=pathlib.Path(temp);build=tmp/'classes';build.mkdir()
        rc,out=run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-proc:none','-source','21','-target','21','-d',str(build),*[str(p) for p in sorted((candidate/'src').glob('*.java'))],str(ROOT/'verifier/ContractTest.java')],tmp)
        if rc:raise RuntimeError('compilation failed: '+out)
        rc,out=run(['java','-Duser.timezone=UTC','-cp',str(build),'ContractTest',str(tmp)],tmp)
        # Exercise the actual config/files/CLI entrypoint as well as service contracts.
        cli_rc,cli=run(['java','-cp',str(build),'Main',str(ROOT/'evidence/site.properties'),str(tmp/'cli.tsv'),'2026-10-27T08:00:00Z','cli-slot','tower-c','2026-10-28T18:00','2026-10-28T19:00','false'],tmp)
        cli_ok=cli_rc==0 and cli.strip()=='201 {"status":"CONFIRMED"}' and (tmp/'cli.tsv').exists()
        return dict(pass_=rc==0 and decision_ok and cli_ok,decisions=decision_ok,cli=cli_ok,behavior_exit=rc,behavior=out.strip().splitlines())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=pathlib.Path);args=parser.parse_args()
    if args.candidate:
        result=verify(args.candidate.resolve());print(json.dumps(result,indent=2));return 0 if result['pass_'] else 1
    results={k:verify(ROOT/k) for k in ['baseline','reference']}
    mutations={
      'dropped_note':('new Booking(site.id(),slot,building,start,end,"CONFIRMED",note)','new Booking(site.id(),slot,building,start,end,"CONFIRMED","")'),
      'server_timezone':('ZoneId zone=site.zone();','ZoneId zone=ZoneId.systemDefault();'),
      'unknown_frees_capacity':('!b.status().equals("CANCELLED")','b.status().equals("CONFIRMED")'),
      'inclusive_cutoff':('!now.isBefore(today.atTime(site.cutoff()).atZone(zone).toInstant())','now.isAfter(today.atTime(site.cutoff()).atZone(zone).toInstant())'),
      'holiday_assumed_open':('if(holidayUnconfirmed)','if(false)')}
    for name,(old,new) in mutations.items():
        with tempfile.TemporaryDirectory(prefix='b01-mutant-') as temp:
            target=pathlib.Path(temp)/'candidate';shutil.copytree(ROOT/'reference',target)
            source=target/'src/Scheduler.java';s=source.read_text();assert old in s;source.write_text(s.replace(old,new))
            results[name]=verify(target)
    with tempfile.TemporaryDirectory(prefix='b01-decision-') as temp:
        target=pathlib.Path(temp)/'candidate';shutil.copytree(ROOT/'reference',target)
        p=target/'decisions.json';d=json.loads(p.read_text());d['holiday']='assume_open';p.write_text(json.dumps(d));results['invented_stakeholder_answer']=verify(target)
    ok=results['reference']['pass_'] and all(not v['pass_'] for k,v in results.items() if k!='reference')
    print(json.dumps({'task':'B01','selfcheck_pass':ok,'results':results},indent=2));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())

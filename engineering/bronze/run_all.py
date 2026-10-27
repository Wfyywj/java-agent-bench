#!/usr/bin/env python3
"""Trusted public fixture checks. This is NOT a security sandbox."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parent
results=[]
for task in ['B01','B02','B03','B04','B05']:
    with tempfile.TemporaryFile() as output:
        process=subprocess.Popen([sys.executable,"-B",str(ROOT/task/'run_selfcheck.py')],cwd=ROOT/task,stdout=output,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+180
        while process.poll() is None:
            if time.monotonic()>deadline or os.fstat(output.fileno()).st_size>1048576:
                process.kill();process.wait();raise RuntimeError(task+' exceeded time/output budget')
            time.sleep(.1)
        output.seek(0);data=output.read(1048577)
        if len(data)>1048576:raise RuntimeError(task+' exceeded output budget')
        results.append({'task':task,'exit_code':process.returncode,'output_sha256':hashlib.sha256(data).hexdigest()})
        if process.returncode:print(data.decode(errors='replace'),file=sys.stderr)
print(json.dumps({'suite':'bronze-engineering-public-dev','passed':all(r['exit_code']==0 for r in results),'results':results},indent=2))
sys.exit(0 if all(r['exit_code']==0 for r in results) else 1)

import json,tempfile,shutil,sys
from pathlib import Path
from verify import bounded,verify

def evaluate(task,candidate):
    src=Path(candidate).resolve()/'src'
    try:
        if not src.is_dir():raise ValueError('candidate must contain src/')
        files=list(src.rglob('*.java'))
        if not files or len(files)>100:raise ValueError('source count outside 1..100')
        if sum(f.stat().st_size for f in files)>1048576:raise ValueError('source size exceeds 1 MiB')
        with tempfile.TemporaryDirectory(prefix=f'candidate-{task}-') as tmp:
            work=Path(tmp);local=work/'src';shutil.copytree(src,local);classes=work/'classes';classes.mkdir()
            rc,out=bounded(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-source','21','-target','21','-d',str(classes),*[str(f) for f in sorted(local.rglob('*.java'))]],work,timeout=30)
            if rc:raise RuntimeError('compile: '+out)
            checks=verify(task,classes,work);passed=all(c['pass_'] for c in checks)
            return {'task':task,'pass':passed,'checks':checks,'security':'trusted local code only, NOT a sandbox'}
    except Exception as e:return {'task':task,'pass':False,'error':str(e)}

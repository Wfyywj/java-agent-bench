#!/usr/bin/env python3
"""Explicit opt-in Maven Central dependency fetch; no system install or committed binary."""
import hashlib,os,urllib.request
from pathlib import Path
URL='https://repo.maven.apache.org/maven2/com/h2database/h2/2.3.232/h2-2.3.232.jar'
SHA='8dae62d22db8982c3dcb3826edb9c727c5d302063a67eef7d63d82de401f07d3'
p=Path(os.environ.get('BENCH_H2_JAR','/tmp/java-agent-bench-h2-2.3.232.jar'))
if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==SHA:print('Verified existing H2:',p)
else:
 data=urllib.request.urlopen(URL,timeout=30).read(4_000_000)
 if hashlib.sha256(data).hexdigest()!=SHA:raise SystemExit('Dependency digest mismatch; refusing write')
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);print('Downloaded verified H2:',p)

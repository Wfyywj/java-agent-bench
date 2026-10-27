#!/usr/bin/env python3
"""Download only frozen Maven Central dependencies. Never regenerate the lock."""
import hashlib,json,pathlib,urllib.request,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=pathlib.Path(os.environ.get('S04_SPRING_DEPS','/tmp/java-agent-bench-s04-spring-deps'))
CACHE.mkdir(parents=True,exist_ok=True)
rows=json.loads((ROOT/'dependencies.lock.json').read_text())
for row in rows:
    p=CACHE/row['file']
    if not p.exists():
        assert row['url'].startswith('https://repo.maven.apache.org/maven2/')
        with urllib.request.urlopen(row['url'],timeout=60) as response:
            data=response.read()
        if hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Downloaded artifact checksum mismatch: '+row['file'])
        p.write_bytes(data)
    if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
        raise ValueError('Cached artifact checksum mismatch: '+str(p))
print('Verified',len(rows),'artifacts')

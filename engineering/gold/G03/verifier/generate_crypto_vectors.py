"""Audit frozen vectors with independent Python standard-library primitives."""
import hashlib,hmac,json,pathlib
p=pathlib.Path(__file__).resolve().parent.parent/'fixtures/crypto-vectors.json'
d=json.loads(p.read_text())
for text,expected in d['hashes'].items():
 assert hashlib.sha256(text.encode('utf-8')).hexdigest()==expected
for x in d['hmac']:
 canonical=(f"{x['session']}:{x['index']}:{x['hash']}" if x['version']==1 else f"v2\n{x['session']}\n{x['index']}\n{x['hash']}")
 assert hmac.new(x['key'].encode('utf-8'),canonical.encode('utf-8'),hashlib.sha256).hexdigest()==x['signature']
print('independent crypto vectors verified')

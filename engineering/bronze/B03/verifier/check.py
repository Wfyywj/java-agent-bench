"""Independent HTTP oracle. Does not import any candidate implementation."""
import base64, csv, json, urllib.request, urllib.error, urllib.parse
from pathlib import Path

def verify(port, dataset):
    base = f'http://127.0.0.1:{port}/boxes?'
    original = dataset.read_text()
    rows = list(csv.DictReader(original.splitlines()))
    checks = {}
    def request(**kw):
        args = dict(tenant='north',status='all',direction='asc',limit=5)
        args.update(kw)
        try:
            with urllib.request.urlopen(base+urllib.parse.urlencode(args),timeout=3) as response:
                raw=response.read(65537)
                assert len(raw)<=65536, 'response exceeds output bound'
                return response.status,json.loads(raw)
        except urllib.error.HTTPError as e:
            return e.code,json.loads(e.read(65536))
    def walk(**kw):
        ids=[]; token=''; pages=0
        for _ in range(30):
            status,p=request(cursor=token,**kw)
            assert status==200, (status,p)
            ids += [b['id'] for b in p['items']]; pages+=1
            token=p['next']
            if token is None: return ids,pages
        raise AssertionError('cursor loop')
    def check(name,fn):
        try: fn(); checks[name]={'pass':True}
        except Exception as e: checks[name]={'pass':False,'reason':str(e)[:400]}
        finally: dataset.write_text(original)
    def ordering():
        for direction in ('asc','desc'):
            for filter_ in ('all','READY','HOLD'):
                expected=[r['id'] for r in sorted((r for r in rows if r['tenant']=='north' and (filter_=='all' or r['status']==filter_)),key=lambda r:(r['receivedAt'],r['id']),reverse=direction=='desc')]
                actual,_=walk(direction=direction,status=filter_,limit=3)
                assert actual==expected, f'{direction}/{filter_} expected {expected}, got {actual}'
    def ties():
        actual,pages=walk(limit=3)
        assert pages>=4 and len(actual)==36 and len(set(actual))==36, f'pages={pages}, count={len(actual)}, unique={len(set(actual))}'
    def malformed():
        tokens=['@@@','a',base64.urlsafe_b64encode(b'1|north').decode(),base64.urlsafe_b64encode(b'2|north|all|asc|2026-01-20T10:00:00Z|BOX002').decode(),base64.urlsafe_b64encode(b'1|north|all|asc|nonsense|BOX002').decode()]
        for token in tokens:
            code,body=request(cursor=token)
            assert (code,body)==(400,{'error':'invalid_request'}),(token,code,body)
    def limits():
        for limit in (0,-1,101,100000,"not-a-number"):
            assert request(limit=limit)==(400,{'error':'invalid_request'}), f'accepted invalid limit {limit}'
        for limit in (1,100):
            code,page=request(limit=limit)
            assert code==200 and len(page['items'])<=limit, (limit,code,page)
    def binding():
        code,page=request(limit=3)
        assert code==200 and page['next']
        for changed in ({'tenant':'south'},{'status':'READY'},{'direction':'desc'}):
            code,body=request(cursor=page['next'],**changed)
            assert (code,body)==(400,{'error':'invalid_request'}),(changed,code,body)
    def changing():
        code,p=request(limit=3); assert code==200
        cursor=p['next']; last=p['items'][-1]
        # Delete a row preceding the cursor; add rows on either side. No offset or snapshot promise.
        changed=[r for r in rows if r['id']!=p['items'][0]['id']]
        changed += [dict(tenant='north',id='NEWBEFORE',receivedAt='2026-01-20T09:59:59Z',status='READY'),dict(tenant='north',id='NEWAFTER',receivedAt='2026-01-20T10:00:03Z',status='READY')]
        with dataset.open('w') as f:
            w=csv.DictWriter(f,fieldnames=['tenant','id','receivedAt','status']); w.writeheader();w.writerows(changed)
        expected=[r['id'] for r in sorted(changed,key=lambda r:(r['receivedAt'],r['id'])) if r['tenant']=='north' and (r['receivedAt'],r['id'])>(last['receivedAt'],last['id'])]
        got=[]
        for _ in range(30):
            code,p=request(cursor=cursor,limit=4);assert code==200
            got += [r['id'] for r in p['items']]
            cursor=p['next']
            if cursor is None:break
        assert got==expected,(got,expected)
        assert request(tenant='missing')[1]=={'items':[],'next':None}
        code,p=request(limit=100); assert code==200 and p['next'] is None
    for name,fn in [('B03-A01',ordering),('B03-A02',ties),('B03-A03',malformed),('B03-A03_limit_bounds',limits),('B03-A04',binding),('B03-A05',changing)]:check(name,fn)
    return checks

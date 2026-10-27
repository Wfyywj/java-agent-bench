"""Public development oracle: HTTP behavior + independent on-disk state assertions."""
import concurrent.futures, json, pathlib, selectors, shutil, subprocess, sys, tempfile, urllib.parse, urllib.request, urllib.error
classes, seed = sys.argv[1:]
results = {}
class Server:
    def __init__(self, directory):
        self.file=pathlib.Path(directory)/'state.tsv'
        if not self.file.exists(): shutil.copyfile(seed,self.file)
        self.p=subprocess.Popen(['java','-Xmx96m','-cp',classes,'App',str(self.file)],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        select=selectors.DefaultSelector();select.register(self.p.stdout,selectors.EVENT_READ)
        if not select.select(5): self.stop(); raise RuntimeError('startup timeout')
        self.port=int(self.p.stdout.readline(32));select.close()
    def stop(self):
        self.p.terminate()
        try:self.p.wait(2)
        except subprocess.TimeoutExpired:self.p.kill();self.p.wait()
    def request(self, **kw):
        args=dict(tenant='tenantA',loan='loan1',token='cabinet77',equipment='bat1',damaged='false');fault=kw.pop('fault',0);args.update(kw)
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/returns',data=urllib.parse.urlencode(args).encode(),headers={'X-Test-Fault':str(fault)})
        try:
            with urllib.request.urlopen(req,timeout=3) as response:return response.status,response.read(4096).decode()
        except urllib.error.HTTPError as e:return e.code,e.read(4096).decode()
    def rows(self):return [line.split('\t') for line in self.file.read_text().splitlines()]
def check(name,fn):
    try:
        with tempfile.TemporaryDirectory() as directory:
            s=Server(directory)
            try:fn(s)
            finally:s.stop()
        results[name]='PASS'
    except Exception as e:results[name]='FAIL: '+str(e)[:200]
def require(ok,msg):
    if not ok:raise AssertionError(msg)
def replay(s):
    first=s.request();second=s.request()
    require(first==second==(200,'loan=loan1;state=CLEANING'),'replay response differs')
    require(next(r[4] for r in s.rows() if r[:2]==['L','loan1'])=='CLEANING','normal return loan state not persisted')
    require(sum(r[0]=='C' for r in s.rows())==1,'duplicate cleaning')
    s.stop();s.__init__(s.file.parent)
    require(s.request()==first,'restart replay differs')
    require(next(r[4] for r in s.rows() if r[:2]==['L','loan1'])=='CLEANING','normal return state lost on restart')
    require(s.request(token='another-token')==(409,'NOT_RETURNABLE'),'second token returned an already-returned loan')
    require(sum(r[0]=='C' for r in s.rows())==1,'restart duplicate cleaning')
check('B02-A01_replay_restart',replay)
def conflicts(s):
    require(s.request()[0]==200,'first return failed')
    for kw in [dict(damaged='true'),dict(equipment='ball2'),dict(loan='loan2',equipment='ball2')]:
        require(s.request(**kw)==(409,'TOKEN_CONFLICT'),'conflicting token accepted')
check('B02-A02_payload_conflicts',conflicts)
for fault in [1,2,3]:
    def rollback(s,fault=fault):
        before=s.file.read_bytes();require(s.request(fault=fault)==(503,'RETRY_LATER'),'fault not surfaced')
        require(s.file.read_bytes()==before,'partial snapshot committed')
        require(s.request()[0]==200,'retry cannot recover')
        require(sum(r[0]=='E' for r in s.rows())==1,'event count')
    check(f'B02-A03_rollback_write_{fault}',rollback)
def authorization(s):
    before=s.file.read_bytes()
    for loan,equipment in [('loan4','cone4'),('loan5','net5')]:require(s.request(loan=loan,equipment=equipment)[0]==409,'invalid lifecycle accepted')
    require(s.request(loan='loan3',equipment='mat3')==s.request(loan='missing')==(404,'NOT_FOUND'),'tenant disclosure')
    require(s.file.read_bytes()==before,'rejected request changed data')
check('B02-A04_tenant_lifecycle',authorization)
def simultaneous(s):
    import threading
    barrier=threading.Barrier(2)
    def send():barrier.wait();return s.request()
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        a=pool.submit(send);b=pool.submit(send);require(a.result()==b.result()==(200,'loan=loan1;state=CLEANING'),'concurrent responses')
    require(next(r[4] for r in s.rows() if r[:2]==['L','loan1'])=='CLEANING','concurrent normal return state not persisted')
    require(sum(r[0]=='E' for r in s.rows())==1 and sum(r[0]=='C' for r in s.rows())==1,'concurrent duplicate effects')
check('B02-A05_concurrent_http',simultaneous)
def damaged(s):
    require(s.request(damaged='true')==(200,'loan=loan1;state=REVIEW'),'damaged not review')
    require(not any(r[0]=='C' for r in s.rows()),'damaged cleaning job')
    require(next(r[4] for r in s.rows() if r[:2]==['L','loan1'])=='REVIEW','damaged available')
check('B02-A05_damaged_review',damaged)
print(json.dumps(results,sort_keys=True));sys.exit(0 if all(v=='PASS' for v in results.values()) else 1)

"""Independent black-box public contract verifier. No candidate imports or oracle delegation."""
import os, selectors, subprocess, time
from pathlib import Path

def bounded(argv,cwd,timeout=15,limit=65536):
    p=subprocess.Popen(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    s=selectors.DefaultSelector();s.register(p.stdout,selectors.EVENT_READ);out=bytearray();deadline=time.monotonic()+timeout
    try:
        while s.get_map():
            if time.monotonic()>deadline:raise RuntimeError('timeout')
            for key,_ in s.select(.1):
                chunk=os.read(key.fileobj.fileno(),8192)
                if not chunk:s.unregister(key.fileobj);continue
                out.extend(chunk)
                if len(out)>limit:raise RuntimeError('output-limit')
        rc=p.wait(timeout=max(.1,deadline-time.monotonic()))
        return rc,out.decode(errors='replace').strip()
    except BaseException:
        import signal
        os.killpg(p.pid,signal.SIGKILL);p.wait();raise
    finally:s.close();p.stdout.close()

# Ordered phase histories. Every request launches a fresh JVM, so each assertion
# also tests durable reconstruction rather than reusing a convenient in-memory state.
SCENARIOS={
'K01':[
('status','none 0 0 0 stable 0'),('promote A 1','TERM 1'),('grant A 1 first 10','ACK first'),('grant A 1 first 10','REPLAY first'),('status','A 1 10 10 cutover 1'),('grant A 1 first 11','REJECT conflict'),('network false','NETWORK false'),('grant A 1 partition 3','REJECT quorum-unavailable'),('status','A 1 10 10 cutover 1'),('control false','CONTROL false'),('promote B 2','REJECT unsafe-promotion'),('network true','NETWORK true'),('control true','CONTROL true'),('promote B 2','TERM 2'),('grant A 1 stale 7','REJECT fenced'),('grant B 2 next 5','ACK next'),('rollback A','TERM 3'),('grant B 2 staleB 7','REJECT fenced'),('grant A 3 zero 0','REJECT amount'),('grant A 3 overflow 9223372036854775807','REJECT long overflow'),('status','A 3 15 15 rollback 2'),('grant A 3 uncertain 4','UNKNOWN after','after'),('grant A 3 uncertain 4','REPLAY uncertain'),('grant A 3 uncommitted 9','UNKNOWN before','before'),('status','A 3 19 19 rollback 3')],
'K02':[
('write u 1 synthetic','WRITTEN'),('view u','1 1 1 1 receipt:1'),('delete u 2','PENDING'),('proof u','PENDING 0'),('step u users','STEP users'),('proof u','PENDING 1'),('write u 3 late','REJECT deleted-subject'),('step u search','STEP search'),('proof u','PENDING 2'),('delete u 1','PENDING'),('step u objects','STEP objects'),('step u analytics','STEP analytics'),('proof u','COMPLETE 2'),('step u users','STEP users'),('view u','0 0 0 0 receipt:1'),('restore u users backup','SUPPRESSED'),('restore u search backup','SUPPRESSED'),('restore u objects backup','SUPPRESSED'),('restore u analytics backup','SUPPRESSED'),('view u','0 0 0 0 receipt:1'),('write other 1 allowed','WRITTEN'),('view other','1 1 1 1 receipt:1'),('step other users','REJECT no-manifest'),('proof other','ACTIVE'),('delete other 2','UNKNOWN after','after'),('proof other','PENDING 0'),('step other users','UNKNOWN before','before'),('view other','1 1 1 1 receipt:1')],
'K03':[
('status','BILLS 0 GATE true'),('shadow 4 3','14 18 BLOCKED'),('status','BILLS 0 GATE false'),('cutover a jan','REJECT gate'),('approve unknown','REJECT policy-unresolved'),('approve peak-correction','APPROVED'),('shadow 4 3','14 18 ALLOWED'),('shadow -1 3','REJECT missing-reading'),('cutover a jan','ROUTE v2'),('bill a jan 4 3','BILL 18 v2'),('bill b jan 4 3','BILL 14 v1'),('bill a feb 4 3','BILL 14 v1'),('rollback a jan','ROUTE v1'),('bill a jan 4 3','BILL 18 v2'),('bill a jan 5 3','REJECT snapshot-conflict'),('status','BILLS 3 GATE true'),('bill c jan 0 3','UNKNOWN after','after'),('cutover c jan','ROUTE v2'),('bill c jan 0 3','BILL 6 v1'),('bill d jan 1 1','UNKNOWN before','before'),('status','BILLS 4 GATE true')],
'K04':[
('book one stranger 1 1','REJECT unauthorized'),('book one member 1 3','REJECT retry-budget'),('book one member 1 1','CONFIRMED one'),('book one member 1 2','CONFIRMED one'),('deliver one','EFFECTS 1'),('deliver one','EFFECTS 1'),('database false','DATABASE false'),('book two member 1 1','REJECT database-unavailable'),('failover','TERM 2'),('book two member 1 1','REJECT stale-connection'),('book two member 2 1','UNKNOWN after','after'),('query two','CONFIRMED two'),('book two member 2 1','CONFIRMED two'),('book three member 2 1','CONFIRMED three'),('book four member 2 1','REJECT full'),('repair 1 apply','REJECT repair-precondition'),('repair 2','DRY_RUN missing=2 term=2'),('status','BOOKINGS 3 EFFECTS 1 TERM 2'),('repair 2 apply','REPAIRED 3'),('repair 2 apply','REPAIRED 3'),('deliver three','EFFECTS 3'),('query four','NOT_FOUND'),('status','BOOKINGS 3 EFFECTS 3 TERM 2')],
'K05':[
('order item1 100','ORDER'),('refund r1 item1 20','REJECT policy'),('policy free-fee','REJECT unresolved-policy'),('policy fee-merchant','POLICY'),('producer 2','REJECT incompatible'),('consumer 2','CONSUMER 2'),('producer 2','PRODUCER 2'),('consumer 1','REJECT incompatible'),('refund r1 item1 20','REFUND'),('refund r1 item1 20','REPLAY'),('refund r1 item1 21','REJECT token-conflict'),('refund r2 item1 81','REJECT refund-limit'),('refund r2 item1 30','REFUND'),('settle item1 99','REJECT before-cutoff'),('settle item1 100','UNKNOWN after','after'),('settle item1 101','PENDING'),('refund r3 item1 1','REJECT closed'),('status','100 50 0 50 2 2'),('reconcile item1','PAID'),('reconcile item1','PAID'),('status','100 50 50 0 2 2'),('producer 1','PRODUCER 1'),('consumer 1','CONSUMER 1'),('status','100 50 50 0 1 1'),('order item2 60','ORDER'),('settle item2 100','PENDING'),('reconcile item2','PAID'),('status','160 50 110 0 1 1')]
}

def verify(task,classes,work):
    results=[]; journal=work/'journal.log'
    def check(label,cmd,expected,fault=None):
        args=['java','-Xmx64m','-cp',str(classes),'Main',str(journal),cmd]
        if fault:args.append(fault)
        rc,out=bounded(args,work)
        results.append(dict(check=label,command=cmd,expected=expected,actual=out,pass_=rc==0 and out==expected))
    for n,case in enumerate(SCENARIOS[task],1):check(f'{task}-C{n:02}',*case)
    # Independent integer oracle over additional approved pricing snapshots.
    if task=='K03':
        for p,o in [(0,0),(1,7),(31,2),(999,100),(5,19)]:check(f'oracle-{p}-{o}',f'shadow {p} {o}',f'{2*(p+o)} {3*p+2*o} ALLOWED')
    # Audit regressions: independent unbounded Python arithmetic must catch
    # narrowing valid Java long readings, not merely wrap/overflow small values.
    if task=='K03':
        journal=work/'numeric-boundaries.log'
        limit=(1<<63)-1
        peak=1<<31
        check('long-v1',f'bill big legacy {peak} 0',f'BILL {peak*2} v1')
        check('long-v1-replay',f'bill big legacy {peak} 0',f'BILL {peak*2} v1')
        check('maximum-v1',f'bill max legacy {limit//2} 0',f'BILL {(limit//2)*2} v1')
        check('overflow-v1',f'bill over legacy {limit//2+1} 0','REJECT long overflow')
        check('addition-overflow-v1',f'bill sum legacy {limit//2} 1','REJECT long overflow')
        check('missing-long',f'bill negative legacy -{peak} 0','REJECT missing-reading')
        check('approve-numeric','approve peak-correction','APPROVED')
        check('long-shadow',f'shadow {peak} {peak}',f'{4*peak} {5*peak} ALLOWED')
        check('route-long','cutover big corrected','ROUTE v2')
        check('long-v2',f'bill big corrected {peak} 0',f'BILL {peak*3} v2')
        check('route-maximum','cutover max corrected','ROUTE v2')
        check('maximum-v2',f'bill max corrected {limit//3} 0',f'BILL {(limit//3)*3} v2')
        check('route-overflow','cutover over corrected','ROUTE v2')
        check('overflow-v2',f'bill over corrected {limit//3+1} 0','REJECT long overflow')
        check('route-addition-overflow','cutover sum corrected','ROUTE v2')
        check('addition-overflow-v2',f'bill sum corrected {limit//3} 1','REJECT long overflow')
        check('overflow-does-not-confirm','status','BILLS 4 GATE true')
        check('route-rollback-long','rollback big corrected','ROUTE v1')
        check('long-pinned-on-rollback',f'bill big corrected {peak} 0',f'BILL {peak*3} v2')
        check('overflow-shadow',f'shadow {limit//2} 0','REJECT long overflow')
        check('failed-shadow-no-side-effect','status','BILLS 4 GATE true')
    if task=='K05':
        journal=work/'cross-item-token.log'
        for label,cmd,expected in [
            ('policy','policy fee-merchant','POLICY'),
            ('first-order','order first 100','ORDER'),
            ('second-order','order second 100','ORDER'),
            ('first-refund','refund global first 20','REFUND'),
            ('pre-conflict-state','status','200 20 0 180 1 1'),
            ('same-amount-different-item','refund global second 20','REJECT token-conflict'),
            ('conflict-no-state-change','status','200 20 0 180 1 1'),
            ('unknown-item-same-token','refund global absent 20','REJECT token-conflict'),
            ('original-token-still-replays','refund global first 20','REPLAY'),
            ('second-independent-refund','refund independent second 80','REFUND'),
            ('independent-refund-conservation','status','200 100 0 100 1 1'),
            ('settle-first','settle first 100','PENDING'),
            ('settle-second','settle second 100','PENDING'),
            ('reconcile-first','reconcile first','PAID'),
            ('reconcile-second','reconcile second','PAID'),
            ('final-conservation','status','200 100 100 0 1 1')]:
            check('cross-item-'+label,cmd,expected)
    # Physical journal validation, never silently discard a possibly acknowledged tail.
    with journal.open('ab') as f:f.write(b'broken-tail')
    check('torn-tail-fail-closed','status','REJECT torn-journal')
    # Independent cross-process contention phase. The OS lock must cover read,
    # validation and forced append; locking only append loses these invariants.
    from concurrent.futures import ThreadPoolExecutor
    journal=work/'contention.log'
    def invoke(command):
        rc,out=bounded(['java','-Xmx64m','-cp',str(classes),'Main',str(journal),command],work)
        return out if rc==0 else 'PROCESS_FAILURE'
    def assert_value(label,actual,expected):
        results.append(dict(check=label,expected=expected,actual=actual,pass_=actual==expected))
    if task=='K01':
        check('contention-bootstrap','promote A 1','TERM 1')
        commands=['grant A 1 same 7']*6
        expected=['ACK same']+['REPLAY same']*5
        final=('status','A 1 7 7 cutover 1')
    elif task=='K02':
        check('contention-seed','write s 1 synthetic','WRITTEN')
        check('contention-manifest','delete s 2','PENDING')
        commands=['step s '+store for store in ['users','search','objects','analytics']]
        expected=['STEP '+store for store in ['users','search','objects','analytics']]
        final=('proof s','COMPLETE 2')
    elif task=='K03':
        commands=['bill concurrent period 5 4']*6
        expected=['BILL 18 v1']*6
        final=('status','BILLS 1 GATE true')
    elif task=='K04':
        commands=['book same member 1 1']*6
        expected=['CONFIRMED same']*6
        final=('status','BOOKINGS 1 EFFECTS 0 TERM 1')
    else:
        check('contention-policy','policy fee-merchant','POLICY')
        check('contention-order','order item 100','ORDER')
        commands=['refund left item 70','refund right item 70']
        expected=['REFUND','REJECT refund-limit']
        final=('status','100 70 0 30 1 1')
    with ThreadPoolExecutor(max_workers=6) as executor:
        outputs=list(executor.map(invoke,commands))
    assert_value('concurrent-linearization',sorted(outputs),sorted(expected))
    check('concurrent-final-state',*final)
    return results

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

public final class Verifier {
    static int failed;
    interface Checked { void run() throws Exception; }
    static void check(boolean v) { if (!v) throw new AssertionError(); }
    static void test(String name, Checked t) { try { t.run(); System.out.println("PASS " + name); } catch(Throwable e) { failed++; System.out.println("FAIL " + name); } }
    static OutboxStore one() { OutboxStore s=new OutboxStore(); s.submit("a",10); return s; }
    static void invalid(Runnable f) { try { f.run(); throw new AssertionError(); } catch(IllegalArgumentException expected) {} }
    static void overflow(Runnable f) { try { f.run(); throw new AssertionError(); } catch(ArithmeticException expected) {} }
    static void race(int n, Checked action) throws Exception {
        ExecutorService pool=Executors.newFixedThreadPool(n);
        CountDownLatch ready=new CountDownLatch(n), start=new CountDownLatch(1);
        List<Future<?>> futures=new ArrayList<>();
        try {
            for(int i=0;i<n;i++) futures.add(pool.submit(()->{ready.countDown(); start.await(); action.run(); return null;}));
            check(ready.await(5,TimeUnit.SECONDS)); start.countDown();
            for(Future<?> f:futures) f.get(5,TimeUnit.SECONDS);
        } finally { start.countDown(); pool.shutdownNow(); check(pool.awaitTermination(5,TimeUnit.SECONDS)); }
    }
    public static void main(String[] args) {
        test("atomic_duplicate",()->{OutboxStore s=one(); check(!s.submit("a",90)); check(s.total()==10 && s.size()==1);});
        test("aggregate_distinct_amounts",()->{OutboxStore s=new OutboxStore(); check(s.submit("a",Integer.MAX_VALUE)); check(s.submit("b",Integer.MAX_VALUE)); check(s.submit("c",7)); check(s.total()==4294967301L && s.size()==3); check(!s.submit("c",9)); check(s.total()==4294967301L);});
        test("dead_after_retries",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); check(s.fail(a,1,0,3)); Claim b=s.claim("w",1,10).orElseThrow(); check(s.fail(b,2,0,3)); Claim c=s.claim("w",2,10).orElseThrow(); check(c.attempt()==3); check(s.fail(c,3,0,3)); check(s.state("a").equals("DEAD") && s.claim("w",100,10).isEmpty());});
        test("invalid_submit_no_effect",()->{OutboxStore s=one(); invalid(()->s.submit("b",-1)); invalid(()->s.submit(" ",1)); invalid(()->s.submit(null,1)); check(s.total()==10 && s.size()==1);});
        test("ordered_claim",()->{OutboxStore s=one(); s.submit("b",2); Claim a=s.claim("w",0,10).orElseThrow(); Claim b=s.claim("x",0,10).orElseThrow(); check(a.id().equals("a") && b.id().equals("b") && a.attempt()==1 && b.token()>a.token()); check(s.claim("z",0,10).isEmpty());});
        test("retry_due_boundary",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); check(s.fail(a,1,9,3)); check(s.claim("w",9,10).isEmpty()); Claim b=s.claim("w",10,10).orElseThrow(); check(b.attempt()==2 && b.token()!=a.token());});
        test("expired_reclaim",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); check(s.claim("x",9,10).isEmpty()); Claim b=s.claim("x",10,10).orElseThrow(); check(b.attempt()==2 && b.token()>a.token());});
        test("stale_token_fencing",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); check(s.fail(a,1,0,3)); Claim b=s.claim("w",1,10).orElseThrow(); check(!s.acknowledge(a,2)); check(!s.fail(a,2,0,3)); check(s.acknowledge(b,2));});
        test("worker_fencing",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); Claim fake=new Claim(a.id(),"intruder",a.token(),a.attempt(),a.leaseUntil()); check(!s.acknowledge(fake,1)); check(!s.fail(fake,1,0,3)); check(s.state("a").equals("CLAIMED"));});
        test("informational_fields_ack",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); Claim changed=new Claim(a.id(),a.worker(),a.token(),999,9999); check(s.acknowledge(changed,1)); check(s.state("a").equals("SENT"));});
        test("informational_fields_fail",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); Claim changed=new Claim(a.id(),a.worker(),a.token(),999,9999); check(s.fail(changed,1,0,3)); check(s.state("a").equals("PENDING")); Claim b=s.claim("w",1,10).orElseThrow(); check(b.attempt()==2);});
        test("expired_completion",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); check(!s.acknowledge(a,10)); check(!s.fail(a,10,0,3)); check(s.state("a").equals("CLAIMED"));});
        test("sent_terminal",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); check(s.acknowledge(a,1)); check(!s.acknowledge(a,2)); check(!s.fail(a,2,0,3)); check(s.claim("w",100,10).isEmpty() && s.state("a").equals("SENT"));});
        test("dead_terminal",()->{OutboxStore s=one(); Claim a=s.claim("w",0,10).orElseThrow(); check(s.fail(a,1,0,1)); check(s.state("a").equals("DEAD") && s.claim("w",100,10).isEmpty());});
        test("invalid_transition_arguments",()->{OutboxStore s=one(); invalid(()->s.claim("",0,10)); invalid(()->s.claim("w",-1,10)); invalid(()->s.claim("w",0,0)); Claim a=s.claim("w",0,10).orElseThrow(); invalid(()->s.fail(a,1,-1,3)); invalid(()->s.fail(a,1,0,0)); invalid(()->s.acknowledge(null,0)); invalid(()->s.acknowledge(a,-1)); check(s.state("a").equals("CLAIMED"));});
        test("overflow_no_mutation",()->{OutboxStore s=one(); overflow(()->s.claim("w",Long.MAX_VALUE,1)); check(s.state("a").equals("PENDING")); Claim a=s.claim("w",0,Long.MAX_VALUE).orElseThrow(); overflow(()->s.fail(a,1,Long.MAX_VALUE,3)); check(s.state("a").equals("CLAIMED"));});
        test("concurrent_duplicate_credit",()->{OutboxStore s=new OutboxStore(); AtomicInteger wins=new AtomicInteger(); race(12,()->{if(s.submit("a",10))wins.incrementAndGet();}); check(wins.get()==1 && s.total()==10 && s.size()==1);});
        test("concurrent_exclusive_claim",()->{OutboxStore s=one(); AtomicInteger wins=new AtomicInteger(); race(12,()->{if(s.claim("w",0,10).isPresent())wins.incrementAndGet();}); check(wins.get()==1);});
        if(failed>0)System.exit(1);
    }
}

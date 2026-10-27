package bench;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import org.springframework.aop.support.AopUtils;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Independent SQL state oracle: no reference implementation is loaded. */
public class IntegrationVerifier {
    interface Checked { void run() throws Exception; }
    static final List<String> failures=new ArrayList<>();
    static void check(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
    static void test(String name,Checked body) {
        try {body.run();System.out.println("PASS "+name);}
        catch(Throwable e){failures.add(name);System.out.println("FAIL "+name+" "+e);}
    }
    static void rejected(Checked body) throws Exception {
        try {body.run();throw new AssertionError("Expected checked business rejection");}
        catch(BusinessFailure expected) {}
    }
    static class Fixture implements AutoCloseable {
        final AnnotationConfigApplicationContext context=new AnnotationConfigApplicationContext();
        final JdbcTemplate sql;
        final BatchService service;
        Fixture(OperationProbe probe) {
            context.registerBean(OperationProbe.class,()->probe);
            context.register(TestConfiguration.class);context.refresh();
            sql=context.getBean(JdbcTemplate.class);service=context.getBean(BatchService.class);
            sql.execute("create table batches(id int primary key)");
            sql.execute("create table inventory(sku int primary key,available int not null check(available>=0))");
            sql.execute("create table orders(id int primary key,batch_id int references batches(id),sku int references inventory(sku),quantity int,state varchar(20))");
            sql.update("insert into batches values(1),(2),(3)");
            sql.update("insert into inventory values(1,11),(2,9)");
            sql.update("insert into orders values(1,1,1,2,'PENDING'),(2,1,1,3,'PENDING'),(3,2,1,4,'PENDING'),(4,3,2,1,'PENDING')");
        }
        int stock(int sku){return sql.queryForObject("select available from inventory where sku=?",Integer.class,sku);}
        String states(int batch){return String.join(",",sql.queryForList("select state from orders where batch_id=? order by id",String.class,batch));}
        String snapshot(){return sql.queryForList("select * from orders order by id").toString()+sql.queryForList("select * from inventory order by sku");}
        public void close(){sql.execute("drop all objects");context.close();}
    }
    static final OperationProbe NONE=new OperationProbe(){};
    static void await(CountDownLatch latch) {
        try {check(latch.await(3,TimeUnit.SECONDS),"barrier timeout");}
        catch(InterruptedException e){Thread.currentThread().interrupt();throw new AssertionError(e);}
    }
    static Object outcome(Checked body){try{body.run();return "OK";}catch(BusinessFailure e){return "REJECTED";}catch(Exception e){throw new CompletionException(e);}}
    static void orderedRace(boolean cancelFirst) throws Exception {
        CountDownLatch locked=new CountDownLatch(1),release=new CountDownLatch(1),started=new CountDownLatch(1);
        AtomicBoolean first=new AtomicBoolean(true);
        OperationProbe p=new OperationProbe(){public void locked(int b){if(b==1&&first.getAndSet(false)){locked.countDown();await(release);}}};
        try(Fixture f=new Fixture(p);ExecutorService pool=Executors.newFixedThreadPool(2)) {
            Future<Object> a=pool.submit(()->outcome(()->{if(cancelFirst)f.service.cancel(1);else f.service.deliver(1);}));
            await(locked);
            Future<Object> b=pool.submit(()->{started.countDown();return outcome(()->{if(cancelFirst)f.service.deliver(1);else f.service.cancel(1);});});
            await(started);release.countDown();
            check(a.get(6,TimeUnit.SECONDS).equals("OK"),"first operation failed");
            check(b.get(6,TimeUnit.SECONDS).equals("REJECTED"),"losing transition must reject");
            check(f.states(1).equals(cancelFirst?"CANCELLED,CANCELLED":"DELIVERED,DELIVERED"),"mixed terminal states");
            check(f.stock(1)==(cancelFirst?16:11),"stock inconsistent with winner");
        } finally {release.countDown();}
    }
    public static void main(String[] args) {
        test("spring-proxy",()->{try(Fixture f=new Fixture(NONE)){check(AopUtils.isCglibProxy(f.service),"not Spring class proxy");}});
        test("active-transaction-at-repository",()->{
            AtomicBoolean observed=new AtomicBoolean();
            try(Fixture f=new Fixture(new OperationProbe(){public void locked(int b){observed.set(TransactionSynchronizationManager.isActualTransactionActive());}})){
                f.service.cancel(1);check(observed.get(),"self-invocation bypassed transaction");
                check(!TransactionSynchronizationManager.isActualTransactionActive(),"transaction leaked");
            }
        });
        test("batch-row-lock-visible-to-independent-connection",()->{
            AtomicReference<Fixture> holder=new AtomicReference<>();
            try(Fixture f=new Fixture(new OperationProbe(){public void locked(int batch){
                try(var connection=holder.get().context.getBean(javax.sql.DataSource.class).getConnection();
                    var statement=connection.createStatement()) {
                    statement.execute("select id from batches where id=1 for update nowait");
                    throw new AssertionError("batch lock absent on independent JDBC connection");
                }catch(java.sql.SQLException expected){check(expected.getErrorCode()==50200,"unexpected SQL failure "+expected);}
            }})){holder.set(f);f.service.cancel(1);}
        });
        test("successful-cancel-atomic-state",()->{try(Fixture f=new Fixture(NONE)){f.service.cancel(1);check(f.states(1).equals("CANCELLED,CANCELLED")&&f.stock(1)==16,"wrong cancellation");}});
        test("unrelated-batch-preserved",()->{try(Fixture f=new Fixture(NONE)){f.service.cancel(1);check(f.states(2).equals("PENDING")&&f.states(3).equals("PENDING")&&f.stock(2)==9,"unrelated mutation");}});
        test("repeat-cancel-idempotent",()->{try(Fixture f=new Fixture(NONE)){f.service.cancel(1);String before=f.snapshot();f.service.cancel(1);check(before.equals(f.snapshot()),"duplicate release");}});
        test("mixed-cancelled-pending-processes-remainder",()->{try(Fixture f=new Fixture(NONE)){
            f.sql.update("update orders set state='CANCELLED' where id=1");
            f.sql.update("update inventory set available=13 where sku=1");
            f.service.cancel(1);
            check(f.states(1).equals("CANCELLED,CANCELLED")&&f.stock(1)==16,"cancelled prefix skipped pending remainder");
            check(f.states(2).equals("PENDING")&&f.stock(2)==9,"unrelated state changed");
        }});
        test("mixed-cancelled-delivered-still-rejects",()->{try(Fixture f=new Fixture(NONE)){
            f.sql.update("update orders set state=case when id=1 then 'CANCELLED' else 'DELIVERED' end where batch_id=1");
            f.sql.update("update inventory set available=13 where sku=1");
            String before=f.snapshot();rejected(()->f.service.cancel(1));
            check(before.equals(f.snapshot()),"mixed terminal rejection mutated state");
        }});
        test("mixed-cancelled-pending-failure-rolls-back",()->{
            try(Fixture f=new Fixture(new OperationProbe(){public void afterOrder(int id)throws BusinessFailure{if(id==2)throw new BusinessFailure("after cancelled prefix");}})){
                f.sql.update("update orders set state='CANCELLED' where id=1");
                f.sql.update("update inventory set available=13 where sku=1");
                String before=f.snapshot();rejected(()->f.service.cancel(1));
                check(before.equals(f.snapshot()),"mixed pending failure partially committed");
            }
        });
        test("checked-mid-batch-rollback",()->{try(Fixture f=new Fixture(new OperationProbe(){public void afterOrder(int id)throws BusinessFailure{if(id==1)throw new BusinessFailure("injected checked");}})){String before=f.snapshot();rejected(()->f.service.cancel(1));check(before.equals(f.snapshot()),"checked failure partially committed");}});
        test("runtime-mid-batch-rollback",()->{try(Fixture f=new Fixture(new OperationProbe(){public void afterOrder(int id){if(id==1)throw new IllegalStateException("injected runtime");}})){String before=f.snapshot();try{f.service.cancel(1);throw new AssertionError("runtime swallowed");}catch(IllegalStateException expected){}check(before.equals(f.snapshot()),"runtime failure partially committed");}});
        test("late-checked-failure-rollback",()->{try(Fixture f=new Fixture(new OperationProbe(){public void afterOrder(int id)throws BusinessFailure{if(id==2)throw new BusinessFailure("late");}})){String before=f.snapshot();rejected(()->f.service.cancel(1));check(before.equals(f.snapshot()),"late failure committed");}});
        test("delivered-order-blocks-whole-batch",()->{try(Fixture f=new Fixture(NONE)){f.sql.update("update orders set state='DELIVERED' where id=2");String before=f.snapshot();rejected(()->f.service.cancel(1));check(before.equals(f.snapshot()),"earlier order not rolled back");}});
        test("delivery-and-repeat-no-release",()->{try(Fixture f=new Fixture(NONE)){f.service.deliver(1);f.service.deliver(1);check(f.states(1).equals("DELIVERED,DELIVERED")&&f.stock(1)==11,"delivery changed available inventory");}});
        test("mixed-delivered-pending-delivers-remainder",()->{try(Fixture f=new Fixture(NONE)){
            f.sql.update("update orders set state='DELIVERED' where id=1");f.service.deliver(1);
            check(f.states(1).equals("DELIVERED,DELIVERED")&&f.stock(1)==11,"delivered prefix skipped pending remainder");
        }});
        test("mixed-delivered-cancelled-rejects-delivery",()->{try(Fixture f=new Fixture(NONE)){
            f.sql.update("update orders set state=case when id=1 then 'DELIVERED' else 'CANCELLED' end where batch_id=1");
            f.sql.update("update inventory set available=14 where sku=1");String before=f.snapshot();
            rejected(()->f.service.deliver(1));check(before.equals(f.snapshot()),"rejected mixed delivery mutated state");
        }});
        test("cancel-wins-concurrent-delivery",()->orderedRace(true));
        test("delivery-wins-concurrent-cancel",()->orderedRace(false));
        test("concurrent-distinct-batches-no-lost-update",()->{
            CyclicBarrier readBarrier=new CyclicBarrier(2);Set<Long> seen=ConcurrentHashMap.newKeySet();
            OperationProbe p=new OperationProbe(){public void beforeRelease(int sku){if(sku==1&&seen.add(Thread.currentThread().threadId()))try{readBarrier.await(3,TimeUnit.SECONDS);}catch(Exception e){throw new AssertionError(e);}}};
            try(Fixture f=new Fixture(p);ExecutorService pool=Executors.newFixedThreadPool(2)){
                Future<Object>a=pool.submit(()->outcome(()->f.service.cancel(1))),b=pool.submit(()->outcome(()->f.service.cancel(2)));
                check(a.get(6,TimeUnit.SECONDS).equals("OK")&&b.get(6,TimeUnit.SECONDS).equals("OK"),"cancel failed");
                check(f.stock(1)==20,"lost inventory increment");check(f.states(1).equals("CANCELLED,CANCELLED")&&f.states(2).equals("CANCELLED"),"missing states");
            }
        });
        test("unrelated-batch-not-globally-locked",()->{
            CountDownLatch locked=new CountDownLatch(1),release=new CountDownLatch(1);
            try(Fixture f=new Fixture(new OperationProbe(){public void locked(int b){if(b==1){locked.countDown();await(release);}}});ExecutorService pool=Executors.newFixedThreadPool(2)){
                Future<Object>a=pool.submit(()->outcome(()->f.service.cancel(1)));await(locked);
                try {Future<Object>b=pool.submit(()->outcome(()->f.service.cancel(3)));check(b.get(2,TimeUnit.SECONDS).equals("OK"),"unrelated blocked");}
                finally {release.countDown();}
                check(a.get(6,TimeUnit.SECONDS).equals("OK"),"first cancel failed");
            }finally{release.countDown();}
        });
        System.out.println("RESULT tests=20 failed="+failures.size());
        if(!failures.isEmpty())System.exit(1);
    }
}

import java.nio.file.*;import java.time.*;import java.util.*;import java.math.*;
public class Verify { static int n=0, failures=0; static void check(String name,boolean ok){ n++;System.out.println((ok?"PASS ":"FAIL ")+name);if(!ok) failures++;} static void reject(String name,Runnable action){boolean bad=false;try{action.run();}catch(Exception e){bad=true;}check(name,bad);} public static void main(String[] args)throws Exception {

Path dir=Files.createTempDirectory("saga");var i=new inventory.Inventory(dir.resolve("i"));var o=new orders.Orders(dir.resolve("o"),i);
var h=new inventory.Inventory.Hold("k","t","camera",10,20);o.create(h,false,true,false);check("unknown reserve outcome queried",i.active()==1);
i.reserve(h,false);check("same request replay one hold",i.active()==1);
reject("key bound to tenant",()->i.reserve(new inventory.Inventory.Hold("k","other","camera",10,20),false));
reject("key bound to lease",()->i.reserve(new inventory.Inventory.Hold("k","t","camera",20,30),false));
reject("overlap capacity",()->i.reserve(new inventory.Inventory.Hold("x","t","camera",19,21),false));
i.reserve(new inventory.Inventory.Hold("adj","t","camera",20,30),false);check("half-open adjacent lease",i.active()==2);
reject("empty interval",()->i.reserve(new inventory.Inventory.Hold("bad","t","camera",20,20),false));
var reopened=new inventory.Inventory(dir.resolve("i"));check("restart preserves holds",reopened.active()==2);
o.create(new inventory.Inventory.Hold("failed","t","tripod",1,2),true,false,true);check("failed commit records pending compensation",o.pending()==1);check("lost release still active",i.active()==3);
var recovery=new orders.Orders(dir.resolve("o"),reopened);reject("recovery requires service role",()->recovery.recover("viewer"));recovery.recover("system-recovery");var finalInv=new inventory.Inventory(dir.resolve("i"));check("restart recovery durably releases",finalInv.active()==2);check("recovery audit",recovery.audits()==1);recovery.recover("system-recovery");check("repeat recovery no audit duplication",recovery.audits()==1);
check("compensation survives second restart",new orders.Orders(dir.resolve("o"),finalInv).pending()==0);
Path concurrent=dir.resolve("concurrent");var c=new inventory.Inventory(concurrent);var gate=new java.util.concurrent.CountDownLatch(1);var success=new java.util.concurrent.atomic.AtomicInteger();var pool=java.util.concurrent.Executors.newFixedThreadPool(2);var fs=new ArrayList<java.util.concurrent.Future<?>>();for(int z=0;z<2;z++){final int id=z;fs.add(pool.submit(()->{try{gate.await();c.reserve(new inventory.Inventory.Hold("c"+id,"t","one",0,10),false);success.incrementAndGet();}catch(Exception expected){}}));}gate.countDown();for(var f:fs)f.get(2,java.util.concurrent.TimeUnit.SECONDS);pool.shutdownNow();check("concurrent capacity one",success.get()==1&&c.active()==1);
System.out.println("INVARIANTS="+n+" FAILURES="+failures);if(failures>0)System.exit(1);}}
package bench;
import java.util.concurrent.*;
public class Main {public static void main(String[] a)throws Exception{
 switch(a[1]){
 case "init" -> {Database.init(a[0]);System.out.println("200 initialized");}
 case "get" -> System.out.println(Database.snapshot(a[0]));
 case "race" -> {
  var start=new CountDownLatch(1);var pool=Executors.newFixedThreadPool(2);
  try{var cancel=pool.submit(()->{start.await();return new TransactionEntry().invoke(a[0],"cancel","none");});
  var ship=pool.submit(()->{start.await();return new TransactionEntry().invoke(a[0],"ship","none");});start.countDown();
  System.out.println(cancel.get()+";"+ship.get()+";"+Database.snapshot(a[0]));}finally{pool.shutdownNow();}
 }
 default -> System.out.println(new TransactionEntry().invoke(a[0],a[1],a.length>2?a[2]:"none"));
 }
}}

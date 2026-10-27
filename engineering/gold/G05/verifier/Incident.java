package bench;
import java.util.concurrent.*;
/** Constructed wait graph, not inferred from a latency threshold. */
public final class Incident {
 public static void main(String[] args)throws Exception{
  ThreadPoolExecutor e=new ThreadPoolExecutor(2,2,0,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<>(2));
  CountDownLatch parents=new CountDownLatch(2),queued=new CountDownLatch(2),allowWait=new CountDownLatch(1);
  Runnable parent=()->{parents.countDown();try{parents.await();Future<Integer> child=e.submit(()->7);queued.countDown();allowWait.await();child.get();}catch(InterruptedException x){Thread.currentThread().interrupt();}catch(ExecutionException x){throw new RuntimeException(x);}};
  try{e.submit(parent);e.submit(parent);if(!queued.await(2,TimeUnit.SECONDS))throw new AssertionError("fixture failed");
   if(e.getActiveCount()!=2||e.getQueue().size()!=2)throw new AssertionError("wait graph precondition");
   System.out.println("parents=2 occupied_workers=2 queued_children=2 available_workers=0");
   System.out.println("parent-A -> child-A -> shared-pool -> parent-A/B; parent-B -> child-B -> shared-pool -> parent-A/B");
   allowWait.countDown();
  }finally{e.shutdownNow();if(!e.awaitTermination(2,TimeUnit.SECONDS))throw new AssertionError("leaked fixture threads");}
 }
}

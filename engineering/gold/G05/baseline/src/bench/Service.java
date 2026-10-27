package bench;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
/** Candidate PR: dispatch both orchestration and downstream calls on one bounded pool. */
public final class Service implements Gateway {
  final ThreadPoolExecutor pool=new ThreadPoolExecutor(2,2,0,TimeUnit.MILLISECONDS,new ArrayBlockingQueue<>(2));
  final AtomicInteger accepted=new AtomicInteger(),rejected=new AtomicInteger();
  public Future<Integer> submit(Callable<Integer> call,boolean independent) {
    try {Future<Integer> result=pool.submit(()->pool.submit(call).get());accepted.incrementAndGet();return result;}
    catch(RejectedExecutionException e){rejected.incrementAndGet();throw e;}
  }
  public Snapshot snapshot(){return new Snapshot(accepted.get(),rejected.get(),0,0,0,2,2,0,0);}
  public void close(){for(Runnable r:pool.shutdownNow())if(r instanceof Future<?> f)f.cancel(true);try{pool.awaitTermination(2,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}}
}

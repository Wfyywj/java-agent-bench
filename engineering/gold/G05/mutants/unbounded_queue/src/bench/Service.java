package bench;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
/** No blocking orchestration worker: caller receives the actual downstream future. */
public final class Service implements Gateway {
  private final ThreadPoolExecutor slow=pool(2,2,"seat"), fast=pool(1,2,"price");
  private final AtomicInteger accepted=new AtomicInteger(), rejected=new AtomicInteger(), completed=new AtomicInteger(), cancelled=new AtomicInteger(), failed=new AtomicInteger();
  private static ThreadPoolExecutor pool(int n,int q,String name) {
    AtomicInteger sequence=new AtomicInteger();
    return new ThreadPoolExecutor(n,n,0,TimeUnit.MILLISECONDS,new LinkedBlockingQueue<>(),r->new Thread(r,name+"-"+sequence.incrementAndGet()),new ThreadPoolExecutor.AbortPolicy());
  }
  public Future<Integer> submit(Callable<Integer> call,boolean independent) {
    ThreadPoolExecutor executor=independent?fast:slow;
    FutureTask<Integer> result=new FutureTask<>(call) {
      protected void done() {
        executor.remove(this);
        if(isCancelled()) cancelled.incrementAndGet();
        else try {get();completed.incrementAndGet();} catch(Exception error){failed.incrementAndGet();}
      }
    };
    accepted.incrementAndGet();
    try {executor.execute(result);} catch(RejectedExecutionException error){accepted.decrementAndGet();rejected.incrementAndGet();throw error;}
    return result;
  }
  public Snapshot snapshot(){return new Snapshot(accepted.get(),rejected.get(),completed.get(),cancelled.get(),failed.get(),slow.getCorePoolSize(),slow.getQueue().remainingCapacity()+slow.getQueue().size(),fast.getCorePoolSize(),fast.getQueue().remainingCapacity()+fast.getQueue().size());}
  public void close(){for(ThreadPoolExecutor e:new ThreadPoolExecutor[]{slow,fast}) {for(Runnable r:e.shutdownNow())if(r instanceof Future<?> f)f.cancel(true);try{if(!e.awaitTermination(2,TimeUnit.SECONDS))throw new IllegalStateException("worker leak");}catch(InterruptedException x){Thread.currentThread().interrupt();throw new IllegalStateException(x);}}}
}

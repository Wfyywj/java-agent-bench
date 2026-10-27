package bench;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
/** Synthetic connection-owning client: interruption must release the lease. */
public final class SeatClient implements Callable<Integer> {
  public final CountDownLatch entered=new CountDownLatch(1), release=new CountDownLatch(1), exited=new CountDownLatch(1);
  public final AtomicInteger leases=new AtomicInteger(), calls=new AtomicInteger();
  public Integer call() throws Exception {
    calls.incrementAndGet(); leases.incrementAndGet(); entered.countDown();
    try { release.await(); return 17; }
    finally { leases.decrementAndGet(); exited.countDown(); }
  }
}

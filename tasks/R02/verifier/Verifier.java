import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public final class Verifier {
    interface Test { void run() throws Exception; }
    static int failed;
    static void require(boolean condition) { if (!condition) throw new AssertionError("contract violated"); }
    static void invalid(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("expected IllegalArgumentException");
    }
    static void test(String name, Test body) {
        try { body.run(); System.out.println("PASS " + name); }
        catch (Throwable failure) { failed++; System.out.println("FAIL " + name); System.err.println(name + ": " + failure); }
    }
    static void parallel(int count, java.util.function.IntConsumer work) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(count);
        CountDownLatch ready = new CountDownLatch(count), start = new CountDownLatch(1);
        List<Future<?>> futures = new ArrayList<>();
        try {
            for (int i = 0; i < count; i++) {
                final int id = i;
                futures.add(pool.submit(() -> { ready.countDown(); try { start.await(); } catch (InterruptedException e) { throw new RuntimeException(e); } work.accept(id); }));
            }
            require(ready.await(5, TimeUnit.SECONDS)); start.countDown();
            for (Future<?> f : futures) f.get(5, TimeUnit.SECONDS);
        } finally { start.countDown(); pool.shutdownNow(); require(pool.awaitTermination(5, TimeUnit.SECONDS)); }
    }
    public static void main(String[] args) {
        test("capacity_validation", () -> { invalid(() -> new Inventory(-1)); require(new Inventory(0).available() == 0); });
        test("exact_capacity", () -> { Inventory i = new Inventory(3); Reservation r = i.reserve("a", 3); require(r.quantity()==3 && r.state()==Reservation.State.ACTIVE && i.available()==0); });
        test("quantity_validation", () -> { Inventory i = new Inventory(4); invalid(() -> i.reserve("a", 0)); invalid(() -> i.reserve("a", -1)); require(i.available()==4); });
        test("id_validation", () -> { Inventory i = new Inventory(4); invalid(() -> i.reserve(null, 1)); invalid(() -> i.reserve(" \t", 1)); invalid(() -> i.cancel(null)); invalid(() -> i.cancel("")); require(i.available()==4); });
        test("insufficient_retry", () -> { Inventory i = new Inventory(4); require(i.reserve("b", 5)==null); require(i.reserve("b", 3)!=null); require(i.available()==1); });
        test("replay_depleted", () -> { Inventory i = new Inventory(3); Reservation r=i.reserve("a",3); require(r.equals(i.reserve("a",3))); require(i.available()==0); });
        test("quantity_conflict", () -> { Inventory i = new Inventory(9); i.reserve("a",3); invalid(() -> i.reserve("a",2)); require(i.available()==6); });
        test("cancel_once", () -> { Inventory i = new Inventory(9); i.reserve("a",3); require(i.cancel("a")); require(!i.cancel("a")); require(i.available()==9); });
        test("unknown_cancel", () -> { Inventory i = new Inventory(9); require(!i.cancel("missing")); require(i.available()==9); });
        test("cancelled_replay_snapshot", () -> { Inventory i=new Inventory(9); Reservation old=i.reserve("a",3); i.cancel("a"); Reservation now=i.reserve("a",3); require(now.state()==Reservation.State.CANCELLED); require(old.state()==Reservation.State.ACTIVE); require(i.available()==9); invalid(() -> i.reserve("a",2)); });
        test("max_capacity_no_overflow", () -> { Inventory i=new Inventory(Integer.MAX_VALUE); i.reserve("a", Integer.MAX_VALUE); require(i.available()==0); require(i.cancel("a")); require(!i.cancel("a")); require(i.available()==Integer.MAX_VALUE); });
        test("reservation_identity_snapshots", () -> {
            Inventory i = new Inventory(10);
            Reservation a = i.reserve(" exact id ", 3), b = i.reserve("other", 2);
            require(a.id().equals(" exact id ") && b.id().equals("other"));
            require(i.reserve(" exact id ", 3).id().equals(" exact id "));
            require(i.cancel(" exact id "));
            Reservation cancelled = i.reserve(" exact id ", 3);
            require(cancelled.id().equals(" exact id ") && cancelled.state()==Reservation.State.CANCELLED);
            require(a.id().equals(" exact id ") && a.state()==Reservation.State.ACTIVE);
        });
        test("concurrent_same_id", () -> { Inventory i=new Inventory(100); parallel(32, n -> require(i.reserve("shared",3)!=null)); require(i.available()==97); });
        test("concurrent_capacity", () -> { Inventory i=new Inventory(10); AtomicInteger successes=new AtomicInteger(); parallel(32, n -> { if(i.reserve("id"+n,1)!=null) successes.incrementAndGet(); }); require(successes.get()==10); require(i.available()==0); });
        test("concurrent_cancel_once", () -> { Inventory i=new Inventory(10); i.reserve("a",7); AtomicInteger successes=new AtomicInteger(); parallel(32,n -> { if(i.cancel("a"))successes.incrementAndGet(); }); require(successes.get()==1 && i.available()==10); });
        if (failed != 0) System.exit(1);
    }
}

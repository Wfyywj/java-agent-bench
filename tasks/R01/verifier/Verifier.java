import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public final class Verifier {
    private static int failures;
    private static final class CountingGateway implements Gateway {
        final AtomicInteger calls = new AtomicInteger();
        public Receipt charge(String tenant, String payload, long amount) {
            return new Receipt(tenant + "-" + calls.incrementAndGet(), amount);
        }
    }
    interface Checked { void run() throws Exception; }
    static void check(boolean condition) { if (!condition) throw new AssertionError(); }
    static void expect(Class<? extends Throwable> type, Checked work) throws Exception {
        try { work.run(); } catch (Throwable e) { if (type.isInstance(e)) return; throw e; }
        throw new AssertionError("expected " + type.getSimpleName());
    }
    static void test(String name, Checked work) {
        try { work.run(); System.out.println("PASS " + name); }
        catch (Throwable e) { failures++; System.out.println("FAIL " + name + " " + e.getClass().getSimpleName()); }
    }
    public static void main(String[] args) {
        test("first_charge", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            Receipt r = s.pay("shop", "key", "cart", 25); check(r.amount() == 25 && g.calls.get() == 1);
        });
        test("gateway_arguments", () -> {
            List<String> tenants = new ArrayList<>(), payloads = new ArrayList<>();
            List<Long> amounts = new ArrayList<>();
            PaymentService service = new PaymentService((t,p,a) -> {
                tenants.add(t); payloads.add(p); amounts.add(a);
                return new Receipt("gateway-" + tenants.size(), a);
            });
            service.pay(" tenant ", "key", " payload ", 37);
            service.pay("other", "key", "different", Long.MAX_VALUE);
            check(tenants.equals(List.of(" tenant ", "other")));
            check(payloads.equals(List.of(" payload ", "different")));
            check(amounts.equals(List.of(37L, Long.MAX_VALUE)));
        });
        test("gateway_receipt_preserved", () -> {
            Receipt authoritative = new Receipt("opaque-gateway-transaction", 99);
            AtomicInteger calls = new AtomicInteger();
            PaymentService service = new PaymentService((t,p,a) -> { calls.incrementAndGet(); return authoritative; });
            check(authoritative.equals(service.pay("shop", "key", "cart", 37)));
            check(authoritative.equals(service.pay("shop", "key", "cart", 37)));
            check(calls.get() == 1);
        });
        test("exact_replay", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            Receipt r = s.pay("shop", "key", "cart", 25);
            check(r.equals(s.pay("shop", "key", "cart", 25)) && g.calls.get() == 1);
        });
        test("payload_conflict", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            s.pay("shop", "key", "cart", 25);
            expect(IllegalStateException.class, () -> s.pay("shop", "key", "other", 25));
            check(g.calls.get() == 1);
        });
        test("amount_conflict", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            s.pay("shop", "key", "cart", 25);
            expect(IllegalStateException.class, () -> s.pay("shop", "key", "cart", 26));
            check(g.calls.get() == 1);
        });
        test("tenant_isolation", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            Receipt a = s.pay("a", "key", "cart", 25), b = s.pay("b", "key", "cart", 25);
            check(!a.equals(b) && g.calls.get() == 2);
        });
        test("composite_key_collision", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            s.pay("a:b", "c", "cart", 1); s.pay("a", "b:c", "cart", 1);
            check(g.calls.get() == 2);
        });
        test("invalid_identifiers", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            for (String invalid : new String[] {null, "", " \t"}) {
                expect(IllegalArgumentException.class, () -> s.pay(invalid, "key", "cart", 1));
                expect(IllegalArgumentException.class, () -> s.pay("shop", invalid, "cart", 1));
                expect(IllegalArgumentException.class, () -> s.pay("shop", "key", invalid, 1));
            }
            check(g.calls.get() == 0);
        });
        test("invalid_amounts", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            for (long amount : new long[] {0, -1, Long.MIN_VALUE})
                expect(IllegalArgumentException.class, () -> s.pay("shop", "key", "cart", amount));
            check(g.calls.get() == 0);
            check(s.pay("shop", "key", "cart", Long.MAX_VALUE).amount() == Long.MAX_VALUE);
        });
        test("retry_after_failure", () -> {
            AtomicInteger calls = new AtomicInteger();
            PaymentService s = new PaymentService((t,p,a) -> {
                if (calls.incrementAndGet() == 1) throw new IllegalArgumentException("gateway unavailable");
                return new Receipt("ok", a);
            });
            expect(IllegalArgumentException.class, () -> s.pay("shop", "key", "old", 1));
            Receipt r = s.pay("shop", "key", "new", 2);
            check(r.equals(s.pay("shop", "key", "new", 2)) && calls.get() == 2);
        });
        test("no_normalization", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            s.pay("shop", "key", "cart", 1); s.pay("shop ", "key", "cart", 1);
            s.pay("shop", "key ", "cart", 1);
            expect(IllegalStateException.class, () -> s.pay("shop", "key", "cart ", 1));
            check(g.calls.get() == 3);
        });
        test("concurrent_replay", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            ExecutorService pool = Executors.newFixedThreadPool(16);
            CountDownLatch ready = new CountDownLatch(16), go = new CountDownLatch(1);
            try {
                List<Future<Receipt>> futures = new ArrayList<>();
                for (int i=0;i<16;i++) futures.add(pool.submit(() -> {
                    ready.countDown(); if (!go.await(3, TimeUnit.SECONDS)) throw new AssertionError();
                    return s.pay("shop", "key", "cart", 9);
                }));
                check(ready.await(3, TimeUnit.SECONDS)); go.countDown();
                Receipt first = futures.get(0).get(3, TimeUnit.SECONDS);
                for (Future<Receipt> f : futures) check(first.equals(f.get(3, TimeUnit.SECONDS)));
                check(g.calls.get() == 1);
            } finally { go.countDown(); pool.shutdownNow(); }
        });
        test("concurrent_conflict", () -> {
            CountingGateway g = new CountingGateway(); PaymentService s = new PaymentService(g);
            ExecutorService pool = Executors.newFixedThreadPool(8);
            CountDownLatch ready = new CountDownLatch(8), go = new CountDownLatch(1);
            try {
                List<Future<Boolean>> futures = new ArrayList<>();
                for (int i=0;i<8;i++) { final int n=i; futures.add(pool.submit(() -> {
                    ready.countDown(); if (!go.await(3, TimeUnit.SECONDS)) throw new AssertionError();
                    try { s.pay("shop", "key", "cart"+n, 9); return true; }
                    catch (IllegalStateException conflict) { return false; }
                })); }
                check(ready.await(3, TimeUnit.SECONDS)); go.countDown(); int winners=0;
                for (Future<Boolean> f : futures) if (f.get(3, TimeUnit.SECONDS)) winners++;
                check(winners == 1 && g.calls.get() == 1);
            } finally { go.countDown(); pool.shutdownNow(); }
        });
        if (failures > 0) System.exit(1);
    }
}

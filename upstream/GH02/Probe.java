import io.github.resilience4j.retry.Retry;
import io.github.resilience4j.retry.RetryConfig;
import java.io.IOException;
import java.util.concurrent.Callable;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

public class Probe {
    private static Retry retryWithIntervals(long first, long later) {
        return Retry.of("inventory", RetryConfig.custom()
                .maxAttempts(4)
                .intervalFunction(attempt -> attempt == 1 ? first : later)
                .build());
    }

    private static void require(boolean passed, String message) {
        if (!passed) {
            throw new AssertionError(message);
        }
    }

    private static void verifyImmediateStop() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        IOException outage = new IOException("inventory unavailable");
        Callable<String> call = Retry.decorateCallable(retryWithIntervals(-1, -1), () -> {
            calls.incrementAndGet();
            throw outage;
        });
        try {
            call.call();
            throw new AssertionError("Callable unexpectedly returned after a failure");
        } catch (Exception actual) {
            require(actual == outage, "Callable must propagate the original IOException, got " + actual);
        }
        require(calls.get() == 1, "Callable attempted " + calls.get() + " calls after an immediate stop");
    }

    private static void verifyLatestFailure() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        IOException first = new IOException("first read failed");
        IOException last = new IOException("second read failed");
        Callable<String> call = Retry.decorateCallable(retryWithIntervals(0, -1), () -> {
            throw calls.incrementAndGet() == 1 ? first : last;
        });
        try {
            call.call();
            throw new AssertionError("Callable unexpectedly returned after two failures");
        } catch (Exception actual) {
            require(actual == last, "Callable must propagate the most recent IOException, got " + actual);
        }
        require(calls.get() == 2, "Expected one retry, got " + calls.get() + " calls");
    }

    private static void verifyRuntimeFailure() {
        AtomicInteger calls = new AtomicInteger();
        IllegalStateException unavailable = new IllegalStateException("supplier unavailable");
        Supplier<String> supplier = Retry.decorateSupplier(retryWithIntervals(-1, -1), () -> {
            calls.incrementAndGet();
            throw unavailable;
        });
        try {
            supplier.get();
            throw new AssertionError("Supplier unexpectedly returned after a failure");
        } catch (RuntimeException actual) {
            require(actual == unavailable, "Supplier lost the original runtime exception: " + actual);
        }
        require(calls.get() == 1, "Supplier attempted " + calls.get() + " calls after an immediate stop");
    }

    private static void verifyRecovery() throws Exception {
        AtomicInteger calls = new AtomicInteger();
        Callable<String> call = Retry.decorateCallable(retryWithIntervals(0, 0), () -> {
            if (calls.incrementAndGet() == 1) {
                throw new IOException("transient failure");
            }
            return "available";
        });
        require("available".equals(call.call()) && calls.get() == 2,
                "A zero interval should permit a second call to succeed");
    }

    @FunctionalInterface
    private interface Scenario {
        void run() throws Exception;
    }

    private static int check(String label, Scenario scenario) {
        try {
            scenario.run();
            System.out.println("PASS " + label);
            return 0;
        } catch (Exception | AssertionError failure) {
            System.out.println("FAIL " + label + " -- " + failure);
            return 1;
        }
    }

    public static void main(String[] args) {
        int failures = check("Callable preserves the first failure on immediate stop", Probe::verifyImmediateStop);
        failures += check("Callable preserves the latest failure after one retry", Probe::verifyLatestFailure);
        failures += check("Supplier preserves the runtime exception on immediate stop", Probe::verifyRuntimeFailure);
        failures += check("Callable recovers on its second attempt with zero delay", Probe::verifyRecovery);
        if (failures > 0) {
            System.exit(1);
        }
    }
}

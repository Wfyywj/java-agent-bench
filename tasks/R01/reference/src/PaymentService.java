import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/** Reference implementation authored directly from the behavioral contract. */
public final class PaymentService {
    private record Scope(String tenant, String key) {}
    private record Completed(String payload, long amount, Receipt receipt) {}
    private final Gateway gateway;
    private final Map<Scope, Completed> completed = new HashMap<>();
    public PaymentService(Gateway gateway) { this.gateway = Objects.requireNonNull(gateway); }
    public synchronized Receipt pay(String tenant, String key, String payload, long amount) {
        if (tenant == null || tenant.isBlank() || key == null || key.isBlank()
                || payload == null || payload.isBlank() || amount <= 0) {
            throw new IllegalArgumentException("nonblank identifiers/payload and positive amount required");
        }
        Scope scope = new Scope(tenant, key);
        Completed previous = completed.get(scope);
        if (previous != null) {
            if (!previous.payload().equals(payload) || previous.amount() != amount) {
                throw new IllegalStateException("idempotency key reused with a different request");
            }
            return previous.receipt();
        }
        Receipt receipt = gateway.charge(tenant, payload, amount);
        completed.put(scope, new Completed(payload, amount, receipt));
        return receipt;
    }
}

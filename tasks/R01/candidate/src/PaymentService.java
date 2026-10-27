import java.util.HashMap;
import java.util.Map;

/** Existing checkout implementation: callers report cross-tenant and retry bugs. */
public final class PaymentService {
    private final Gateway gateway;
    private final Map<String, Receipt> receipts = new HashMap<>();
    public PaymentService(Gateway gateway) { this.gateway = gateway; }
    public Receipt pay(String tenant, String key, String payload, long amount) {
        Receipt cached = receipts.get(key);
        if (cached != null) return cached;
        Receipt receipt = gateway.charge(tenant, payload, amount);
        receipts.put(key, receipt);
        return receipt;
    }
}

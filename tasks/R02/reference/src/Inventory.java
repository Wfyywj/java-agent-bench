import java.util.HashMap;
import java.util.Map;

/** Independent specification implementation: a single monitor owns all state. */
public final class Inventory {
    private int available;
    private final Map<String, Reservation> ledger = new HashMap<>();
    public Inventory(int capacity) {
        if (capacity < 0) throw new IllegalArgumentException("negative capacity");
        available = capacity;
    }
    private static void validateId(String id) {
        if (id == null || id.isBlank()) throw new IllegalArgumentException("blank id");
    }
    public synchronized int available() { return available; }
    public synchronized Reservation reserve(String id, int quantity) {
        validateId(id);
        if (quantity <= 0) throw new IllegalArgumentException("nonpositive quantity");
        Reservation prior = ledger.get(id);
        if (prior != null) {
            if (prior.quantity() != quantity) throw new IllegalArgumentException("quantity conflict");
            return prior;
        }
        if (quantity > available) return null;
        Reservation created = new Reservation(id, quantity, Reservation.State.ACTIVE);
        ledger.put(id, created);
        available -= quantity;
        return created;
    }
    public synchronized boolean cancel(String id) {
        validateId(id);
        Reservation prior = ledger.get(id);
        if (prior == null || prior.state() == Reservation.State.CANCELLED) return false;
        ledger.put(id, new Reservation(id, prior.quantity(), Reservation.State.CANCELLED));
        available += prior.quantity();
        return true;
    }
}

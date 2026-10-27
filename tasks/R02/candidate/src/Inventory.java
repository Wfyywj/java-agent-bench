import java.util.HashMap;
import java.util.Map;

/** In-memory inventory component; repair its business invariants. */
public final class Inventory {
    private int available;
    private final Map<String, Reservation> reservations = new HashMap<>();
    public Inventory(int capacity) { this.available = capacity; }
    public synchronized int available() { return available; }
    public synchronized Reservation reserve(String id, int quantity) {
        if (available < quantity) return null;
        Reservation value = new Reservation(id, quantity, Reservation.State.ACTIVE);
        available -= quantity;
        reservations.put(id, value);
        return value;
    }
    public synchronized boolean cancel(String id) {
        Reservation value = reservations.get(id);
        if (value == null) return false;
        available += value.quantity();
        return true;
    }
}

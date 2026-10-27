import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/** In-memory transaction boundary: aggregate and outbox mutations share this monitor. */
public final class OutboxStore {
    private final Map<String, OutboxMessage> messages = new LinkedHashMap<>();
    private long total; private long sequence;
    public synchronized boolean submit(String id, int amount) {
        if (id == null || id.isBlank() || amount <= 0) throw new IllegalArgumentException();
        if (messages.containsKey(id)) return false;
        long next = Math.addExact(total, amount);
        messages.put(id, new OutboxMessage(id, amount)); total = next;
        return true;
    }
    public synchronized Optional<Claim> claim(String worker, long now, long lease) {
        if (worker == null || worker.isBlank() || now < 0 || lease <= 0) throw new IllegalArgumentException();
        long until = Math.addExact(now, lease);
        for (OutboxMessage m : messages.values()) {
            if ((m.state.equals("PENDING") && m.due <= now) ||
                (m.state.equals("CLAIMED") && m.leaseUntil <= now)) {
                m.state = "CLAIMED"; m.worker = worker; m.token = ++sequence;
                m.leaseUntil = until; m.attempts++;
                return Optional.of(new Claim(m.id, worker, m.token, m.attempts, until));
            }
        }
        return Optional.empty();
    }
    private boolean owns(OutboxMessage m, Claim c, long now) {
        return m != null && m.state.equals("CLAIMED") && m.token == c.token()
            && m.worker.equals(c.worker()) && now < m.leaseUntil;
    }
    public synchronized boolean acknowledge(Claim c, long now) {
        if (c == null || now < 0) throw new IllegalArgumentException();
        OutboxMessage m = messages.get(c.id());
        if (!owns(m, c, now)) return false;
        m.state = "SENT"; return true;
    }
    public synchronized boolean fail(Claim c, long now, long backoff, int maxAttempts) {
        if (c == null || now < 0 || backoff < 0 || maxAttempts < 1) throw new IllegalArgumentException();
        long due = Math.addExact(now, backoff);
        OutboxMessage m = messages.get(c.id());
        if (!owns(m, c, now)) return false;
        m.state = m.attempts >= maxAttempts ? "DEAD" : "PENDING";
        m.due = due; return true;
    }
    public synchronized long total() { return total; }
    public synchronized int size() { return messages.size(); }
    public synchronized String state(String id) { return messages.containsKey(id) ? messages.get(id).state : "MISSING"; }
}

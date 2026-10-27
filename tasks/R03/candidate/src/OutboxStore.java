import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/** Legacy dispatcher implementation; complete the contract in PROMPT.md. */
public final class OutboxStore {
    private final Map<String, OutboxMessage> messages = new LinkedHashMap<>();
    private long total; private long sequence;
    public boolean submit(String id, int amount) {
        total += amount;
        if (messages.containsKey(id)) return false;
        messages.put(id, new OutboxMessage(id, amount)); return true;
    }
    public Optional<Claim> claim(String worker, long now, long lease) {
        for (OutboxMessage m : messages.values()) {
            if (m.state.equals("PENDING")) {
                m.state = "CLAIMED"; m.worker = worker; m.token = ++sequence;
                m.leaseUntil = now + lease; m.attempts++;
                return Optional.of(new Claim(m.id, worker, m.token, m.attempts, m.leaseUntil));
            }
        }
        return Optional.empty();
    }
    public boolean acknowledge(Claim c, long now) {
        OutboxMessage m = messages.get(c.id());
        if (m == null) return false;
        m.state = "SENT"; return true;
    }
    public boolean fail(Claim c, long now, long backoff, int maxAttempts) {
        OutboxMessage m = messages.get(c.id());
        if (m == null) return false;
        m.state = "PENDING"; m.due = now + backoff; return true;
    }
    public long total() { return total; }
    public int size() { return messages.size(); }
    public String state(String id) { return messages.containsKey(id) ? messages.get(id).state : "MISSING"; }
}

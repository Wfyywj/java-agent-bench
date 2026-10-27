import java.time.Instant;
public record Box(String tenant, String id, Instant receivedAt, String status) {}

public final class OutboxMessage {
    final String id; final int amount;
    String state = "PENDING"; String worker; long token; long due; long leaseUntil; int attempts;
    OutboxMessage(String id, int amount) { this.id = id; this.amount = amount; }
}

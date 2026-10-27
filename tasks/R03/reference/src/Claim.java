public record Claim(String id, String worker, long token, int attempt, long leaseUntil) {}

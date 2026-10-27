public final class AuditLog {
    public static void rejected(Quote quote) {
        System.err.println("quote_rejected code=INVALID_QUOTE");
    }
}

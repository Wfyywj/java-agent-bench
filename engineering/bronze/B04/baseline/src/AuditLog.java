public final class AuditLog {
    public static void rejected(Quote quote) {
        System.err.println("quote_rejected note=" + (quote == null ? "" : quote.note()));
    }
}

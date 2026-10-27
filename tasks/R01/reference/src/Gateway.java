public interface Gateway {
    Receipt charge(String tenant, String payload, long amount);
}

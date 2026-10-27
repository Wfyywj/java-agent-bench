/** A reservation snapshot. Returned values must remain immutable. */
public record Reservation(String id, int quantity, State state) {
    public enum State { ACTIVE, CANCELLED }
}

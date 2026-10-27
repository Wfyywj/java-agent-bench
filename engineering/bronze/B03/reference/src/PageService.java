import java.io.IOException;
import java.util.*;
public final class PageService {
    private final BoxRepository repository;
    public PageService(BoxRepository repository) { this.repository = repository; }
    public record Page(List<Box> items, String next) {}
    public Page query(String tenant, String filter, String direction, int limit, String token) throws IOException {
        if (!tenant.matches("[A-Za-z0-9_-]+") || !Set.of("all","READY","HOLD").contains(filter)
            || !Set.of("asc","desc").contains(direction) || limit < 1 || limit > 100) throw new IllegalArgumentException("invalid_query");
        Cursor cursor = token.isEmpty() ? null : Cursor.decode(token, tenant, filter, direction);
        Comparator<Box> order = Comparator.comparing(Box::receivedAt).thenComparing(Box::id);
        if (direction.equals("desc")) order = order.reversed();
        final Comparator<Box> sorted = order;
        Box after = cursor == null ? null : new Box(tenant, cursor.id(), cursor.time(), filter);
        var candidates = repository.read().stream()
            .filter(b -> b.tenant().equals(tenant) && (filter.equals("all") || b.status().equals(filter)))
            .sorted(sorted).filter(b -> after == null || sorted.compare(b, after) > 0).limit(limit + 1L).toList();
        var items = List.copyOf(candidates.subList(0, Math.min(limit, candidates.size())));
        String next = null;
        if (candidates.size() > limit) {
            Box last = items.getLast();
            next = new Cursor(tenant, filter, direction, last.receivedAt(), last.id()).encode();
        }
        return new Page(items, next);
    }
}

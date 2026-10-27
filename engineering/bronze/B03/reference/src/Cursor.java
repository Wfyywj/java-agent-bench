import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
public record Cursor(String tenant, String filter, String direction, Instant time, String id) {
    public String encode() {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(
            ("1|"+tenant+"|"+filter+"|"+direction+"|"+time+"|"+id).getBytes(StandardCharsets.UTF_8));
    }
    public static Cursor decode(String token, String tenant, String filter, String direction) {
        try {
            if (token.length() > 1024) throw new IllegalArgumentException();
            String[] f = new String(Base64.getUrlDecoder().decode(token), StandardCharsets.UTF_8).split("\\|", -1);
            if (f.length != 6 || !f[0].equals("1") || !f[5].matches("[A-Za-z0-9_-]+")) throw new IllegalArgumentException();
            if (!f[1].equals(tenant) || !f[2].equals(filter) || !f[3].equals(direction)) throw new IllegalArgumentException();
            return new Cursor(f[1], f[2], f[3], Instant.parse(f[4]), f[5]);
        } catch (RuntimeException e) { throw new IllegalArgumentException("invalid_cursor"); }
    }
}

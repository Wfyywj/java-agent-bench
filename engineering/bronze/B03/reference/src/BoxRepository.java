import java.nio.file.*;
import java.io.IOException;
import java.time.Instant;
import java.util.*;
/** Reloaded for every request: intentionally not snapshot isolation. */
public final class BoxRepository {
    private final Path file;
    public BoxRepository(Path file) { this.file = file; }
    public List<Box> read() throws IOException {
        var rows = new ArrayList<Box>();
        var lines = Files.readAllLines(file);
        for (String line : lines.subList(1, lines.size())) {
            String[] f = line.split(",", -1);
            if (f.length != 4) throw new IOException("invalid warehouse export");
            rows.add(new Box(f[0], f[1], Instant.parse(f[2]), f[3]));
        }
        return rows;
    }
}

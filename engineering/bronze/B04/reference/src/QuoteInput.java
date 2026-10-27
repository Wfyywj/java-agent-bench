import java.math.BigDecimal;
import java.util.Arrays;
public final class QuoteInput {
    public static Quote parse(String row) {
        String[] fields = row.split("\t", -1);
        if (fields.length != 4) throw new IllegalArgumentException("shape");
        return new Quote(Arrays.stream(fields[0].split(",")).map(BigDecimal::new).toList(),
            fields[1].equals("-") ? null : new BigDecimal(fields[1]),
            new BigDecimal(fields[2]), fields[3]);
    }
}

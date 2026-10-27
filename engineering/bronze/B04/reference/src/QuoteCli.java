import java.io.*;
import java.nio.charset.StandardCharsets;
public final class QuoteCli {
    public static void main(String[] args) throws Exception {
        try (var reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String row;
            while ((row = reader.readLine()) != null) {
                Quote quote = null;
                try {
                    quote = QuoteInput.parse(row);
                    System.out.println("OK\t" + QuoteCalculator.total(quote).toPlainString());
                } catch (IllegalArgumentException e) {
                    AuditLog.rejected(quote);
                    System.out.println("ERROR\t422\tINVALID_QUOTE");
                } catch (RuntimeException e) {
                    AuditLog.rejected(quote);
                    System.out.println("ERROR\t500\tINTERNAL");
                }
            }
        }
    }
}

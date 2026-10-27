import java.math.BigDecimal;
import java.math.RoundingMode;
public final class QuoteCalculator {
    private static final BigDecimal MAX = new BigDecimal("999999999.99");
    public static BigDecimal total(Quote quote) {
        BigDecimal discount = quote.discount();
        validate(quote, discount);
        double running = 0;
        for (BigDecimal line : quote.lines()) {
            double discounted = Math.round(line.doubleValue() * (1 - discount.doubleValue()) * 100) / 100.0;
            double tax = Math.round(discounted * quote.tax().doubleValue() * 100) / 100.0;
            running += discounted + tax;
        }
        BigDecimal total = BigDecimal.valueOf(running).setScale(2, RoundingMode.HALF_UP);
        if (total.compareTo(MAX) > 0) throw new IllegalArgumentException("overflow");
        return total;
    }
    private static void validate(Quote quote, BigDecimal discount) {
        if (discount.compareTo(BigDecimal.ZERO) < 0 || discount.compareTo(BigDecimal.ONE) > 0)
            throw new IllegalArgumentException("discount");
        if (quote.tax().signum() < 0 || quote.tax().compareTo(BigDecimal.ONE) > 0 || quote.lines().isEmpty())
            throw new IllegalArgumentException("tax or empty");
        for (BigDecimal line : quote.lines())
            if (line.signum() < 0 || line.compareTo(MAX) > 0) throw new IllegalArgumentException("line");
    }
}

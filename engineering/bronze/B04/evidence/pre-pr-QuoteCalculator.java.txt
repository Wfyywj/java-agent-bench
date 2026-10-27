import java.math.BigDecimal;
import java.math.RoundingMode;
public final class QuoteCalculator {
    private static final BigDecimal MAX = new BigDecimal("999999999.99");
    public static BigDecimal total(Quote quote) {
        BigDecimal discount = quote.discount() == null ? BigDecimal.ZERO : quote.discount();
        validate(quote, discount);
        BigDecimal subtotal = BigDecimal.ZERO;
        for (BigDecimal line : quote.lines()) {
            subtotal = subtotal.add(line.multiply(BigDecimal.ONE.subtract(discount)).setScale(2, RoundingMode.HALF_UP));
        }
        BigDecimal tax = subtotal.multiply(quote.tax()).setScale(2, RoundingMode.HALF_UP);
        BigDecimal total = subtotal.add(tax).setScale(2, RoundingMode.HALF_UP);
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

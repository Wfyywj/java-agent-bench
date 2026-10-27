import java.math.BigDecimal;
import java.util.List;
public record Quote(List<BigDecimal> lines, BigDecimal discount, BigDecimal tax, String note) {}

package bench;
import javax.sql.DataSource;
import org.h2.jdbcx.JdbcDataSource;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.EnableTransactionManagement;

@Configuration
@EnableTransactionManagement(proxyTargetClass=true)
public class TestConfiguration {
    @Bean public DataSource dataSource() {
        JdbcDataSource ds=new JdbcDataSource();
        ds.setURL("jdbc:h2:mem:"+java.util.UUID.randomUUID()+";DB_CLOSE_DELAY=-1;LOCK_TIMEOUT=4000");
        return ds;
    }
    @Bean public JdbcTemplate jdbc(DataSource ds) {return new JdbcTemplate(ds);}
    @Bean public PlatformTransactionManager transactionManager(DataSource ds) {
        return new DataSourceTransactionManager(ds);
    }
    @Bean public OrderRepository orders(JdbcTemplate jdbc) {return new OrderRepository(jdbc);}
    @Bean public BatchService service(OrderRepository orders,OperationProbe probe) {
        return new BatchService(orders,probe);
    }
}

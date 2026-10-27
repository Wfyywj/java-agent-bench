package bench;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;

public class OrderRepository {
    private final JdbcTemplate jdbc;
    public OrderRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }
    public void lockBatch(int batch) {
        jdbc.queryForObject("select id from batches where id=?", Integer.class, batch);
    }
    public List<OrderRow> orders(int batch) {
        return jdbc.query("select id,sku,quantity,state from orders where batch_id=? order by id",
            (rs,n) -> new OrderRow(rs.getInt(1),rs.getInt(2),rs.getInt(3),rs.getString(4)), batch);
    }
    public void transition(int id, String state) {
        int count=jdbc.update("update orders set state=? where id=? and state='PENDING'",state,id);
        if(count!=1) throw new IllegalStateException("Concurrent order transition");
    }
    public void release(OrderRow order, OperationProbe probe) throws BusinessFailure {
        // This read is for observation; never use its snapshot as the write value.
        int available=jdbc.queryForObject("select available from inventory where sku=?",Integer.class,order.sku());
        probe.beforeRelease(order.sku());
        jdbc.update("update inventory set available=available+? where sku=?",order.quantity(),order.sku());
    }
}

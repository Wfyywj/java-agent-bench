package bench;
import org.springframework.transaction.annotation.Transactional;

public class BatchService {
    private final OrderRepository orders;
    private final OperationProbe probe;
    public BatchService(OrderRepository orders, OperationProbe probe) {
        this.orders=orders; this.probe=probe;
    }
    // Entry boundary must include every order and roll back checked domain failures.
    @Transactional(rollbackFor=BusinessFailure.class)
    public void cancel(int batch) throws BusinessFailure {
        try { cancelInside(batch); } catch (BusinessFailure ignored) {}
    }
    @Transactional(rollbackFor=BusinessFailure.class)
    public void cancelInside(int batch) throws BusinessFailure {
        orders.lockBatch(batch);
        probe.locked(batch);
        for (OrderRow order : orders.orders(batch)) {
            if (order.state().equals("DELIVERED")) throw new BusinessFailure("Already delivered");
            if (order.state().equals("CANCELLED")) continue;
            orders.release(order,probe);
            orders.transition(order.id(),"CANCELLED");
            probe.afterOrder(order.id());
        }
    }
    @Transactional(rollbackFor=BusinessFailure.class)
    public void deliver(int batch) throws BusinessFailure {
        orders.lockBatch(batch);
        probe.locked(batch);
        for (OrderRow order : orders.orders(batch)) {
            if(order.state().equals("CANCELLED")) throw new BusinessFailure("Already cancelled");
            if(order.state().equals("DELIVERED")) continue;
            orders.transition(order.id(),"DELIVERED");
            probe.afterOrder(order.id());
        }
    }
}

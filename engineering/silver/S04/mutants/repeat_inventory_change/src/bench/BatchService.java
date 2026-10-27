package bench;
import java.sql.*;
public final class BatchService implements BatchActions {
 private final Connection c;public BatchService(Connection c){this.c=c;}
 public String execute(String action,String fault)throws Exception{
  String batch;try(var s=c.createStatement();var r=s.executeQuery("SELECT status FROM batch WHERE id=1 FOR UPDATE")){r.next();batch=r.getString(1);}
  if(action.equals("ship")){
   if(batch.equals("CANCELLED"))return "409 cancelled";
   try(var s=c.createStatement()){s.executeUpdate("UPDATE orders SET status='SHIPPED' WHERE id=1");}return "200 shipped";
  }
  if(batch.equals("CANCELLED")){try(var s=c.createStatement()){s.executeUpdate("UPDATE inventory SET available=available-1 WHERE id=1");}return "200 duplicate";}
  try(var s=c.createStatement();var r=s.executeQuery("SELECT COUNT(*) FROM orders WHERE batch_id=1 AND status='SHIPPED'")){r.next();if(r.getInt(1)>0)return "409 shipped";}
  try(var s=c.createStatement()){
   s.executeUpdate("UPDATE orders SET status='CANCELLED' WHERE id=1");s.executeUpdate("UPDATE inventory SET available=available+2 WHERE id=1");
   if(fault.equals("middle"))throw new IllegalStateException("injected_runtime_failure");
   if(fault.equals("checked"))throw new Exception("injected_checked_failure");
   s.executeUpdate("UPDATE orders SET status='CANCELLED' WHERE id=2");s.executeUpdate("UPDATE inventory SET available=available+3 WHERE id=1");
   s.executeUpdate("UPDATE batch SET status='CANCELLED' WHERE id=1");
  }return "200 cancelled";
 }
}

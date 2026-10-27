package bench;
import java.sql.*;import java.util.*;
public final class SearchRepository {
 public int queries=0;
 public static final String SQL="SELECT o.id,o.tenant,o.created FROM orders o WHERE o.tenant=? AND EXISTS(SELECT 1 FROM messages m WHERE m.tenant=o.tenant AND m.order_id=o.id AND m.created>=?) ORDER BY o.created DESC,o.id ASC LIMIT ?";
 public List<Order> search(Connection c,String tenant,long since,int limit)throws Exception{
  List<Order> result=new ArrayList<>();
  try(var p=c.prepareStatement(SQL)){p.setString(1,tenant);p.setLong(2,since);p.setInt(3,limit);queries++;
   try(var r=p.executeQuery()){while(r.next())result.add(new Order(r.getString(1),r.getString(2),r.getLong(3)));}
  }
  for(Order o:result){try(var p=c.prepareStatement("SELECT COUNT(*) FROM messages WHERE order_id=?")){p.setString(1,o.id());queries++;try(var ignored=p.executeQuery()){ignored.next();}}}
  return result;
 }
 public String explain(Connection c)throws Exception{try(var p=c.prepareStatement("EXPLAIN "+SQL)){p.setString(1,"t1");p.setLong(2,1700);p.setInt(3,100);try(var r=p.executeQuery()){r.next();return r.getString(1);}}}
}

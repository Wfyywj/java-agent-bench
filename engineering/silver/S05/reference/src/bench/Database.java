package bench;
import java.sql.*;import java.nio.file.*;
public final class Database {
 public static Connection load(Path root)throws Exception{
  var c=DriverManager.getConnection("jdbc:h2:mem:search","sa","");
  try(var s=c.createStatement()){
   s.execute("CREATE TABLE orders(id VARCHAR PRIMARY KEY,tenant VARCHAR NOT NULL,created BIGINT NOT NULL)");
   s.execute("CREATE TABLE messages(tenant VARCHAR NOT NULL,order_id VARCHAR NOT NULL,created BIGINT NOT NULL)");
   s.execute("CREATE INDEX idx_orders_tenant_created ON orders(tenant,created DESC,id)");
   s.execute("CREATE INDEX idx_messages_recent ON messages(tenant,order_id,created)");
  }
  try(var p=c.prepareStatement("INSERT INTO orders VALUES(?,?,?)")){for(String line:Files.readAllLines(root.resolve("orders.csv"))){String[] x=line.split(",");p.setString(1,x[0]);p.setString(2,x[1]);p.setLong(3,Long.parseLong(x[2]));p.addBatch();}p.executeBatch();}
  try(var p=c.prepareStatement("INSERT INTO messages VALUES(?,?,?)")){for(String line:Files.readAllLines(root.resolve("conversations.csv"))){String[] x=line.split(",");p.setString(1,x[0]);p.setString(2,x[1]);p.setLong(3,Long.parseLong(x[2]));p.addBatch();}p.executeBatch();}
  return c;
 }
}

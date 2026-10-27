package evaluation;
import java.sql.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;
import bench.SearchRepository;
/** Evaluator-owned fixture and JDBC instrumentation; never copied into candidate packages. */
public final class TrustedSearchProbe {
 static Object delegate(Object target,Method method,Object[] args)throws Throwable {
  try{return method.invoke(target,args);}catch(InvocationTargetException e){throw e.getCause();}
 }
 static Connection instrument(Connection actual,AtomicInteger count){
  return (Connection)Proxy.newProxyInstance(Connection.class.getClassLoader(),new Class<?>[]{Connection.class},(proxy,m,args)->{
   Object returned=delegate(actual,m,args);
   if(returned instanceof Statement statement){
    Class<?> api=returned instanceof CallableStatement?CallableStatement.class:returned instanceof PreparedStatement?PreparedStatement.class:Statement.class;
    return Proxy.newProxyInstance(Statement.class.getClassLoader(),new Class<?>[]{api},(ignored,sm,sa)->{
     if(sm.getName().startsWith("execute"))count.incrementAndGet();
     if(sm.getName().equals("getConnection"))return proxy;
     return delegate(statement,sm,sa);
    });
   }return returned;
  });
 }
 static Connection fixture(Path root)throws Exception{
  Connection c=DriverManager.getConnection("jdbc:h2:mem:trusted_probe","sa","");
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
 public static void main(String[] a)throws Exception{
  try(Connection actual=fixture(Path.of(a[0]))){
   AtomicInteger executions=new AtomicInteger();
   var results=new SearchRepository().search(instrument(actual,executions),a[1],Long.parseLong(a[2]),Integer.parseInt(a[3]));
   System.out.println("200 "+results.stream().map(bench.Order::id).collect(Collectors.joining(","))+"|observed_executions="+executions.get());
  }
 }
}

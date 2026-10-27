package bench;
import java.lang.reflect.*;
public final class TransactionEntry {
 // Real JDK dynamic proxy and JDBC transaction. Not Spring AOP.
 public String invoke(String dir,String action,String fault)throws Exception{
  BatchActions proxy=(BatchActions)Proxy.newProxyInstance(BatchActions.class.getClassLoader(),new Class<?>[]{BatchActions.class},(ignored,method,args)->{
   try(var c=Database.open(dir)){
    c.setAutoCommit(false);
    try{Object out=method.invoke(new BatchService(c),args);c.commit();return out;}
    catch(InvocationTargetException failure){c.rollback();return "503 rolled_back";}
   }
  });
  return proxy.execute(action,fault);
 }
}

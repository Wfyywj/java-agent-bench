package bench;
import java.sql.*;import java.nio.file.*;
public final class Database {
 public static Connection open(String dir)throws Exception{Files.createDirectories(Path.of(dir));return DriverManager.getConnection("jdbc:h2:"+Path.of(dir).resolve("batch").toAbsolutePath()+";LOCK_TIMEOUT=4000","sa","");}
 public static void init(String dir)throws Exception{try(var c=open(dir);var st=c.createStatement()){
 st.execute("CREATE TABLE batch(id INT PRIMARY KEY,status VARCHAR NOT NULL)");
 st.execute("CREATE TABLE orders(id INT PRIMARY KEY,batch_id INT NOT NULL REFERENCES batch(id),status VARCHAR NOT NULL,quantity INT NOT NULL)");
 st.execute("CREATE TABLE inventory(id INT PRIMARY KEY,available INT CHECK(available BETWEEN 0 AND 10))");
 st.execute("INSERT INTO batch VALUES(1,'OPEN')");st.execute("INSERT INTO orders VALUES(1,1,'PENDING',2),(2,1,'PENDING',3)");st.execute("INSERT INTO inventory VALUES(1,5)");}}
 public static String snapshot(String dir)throws Exception{try(var c=open(dir);var st=c.createStatement();var r=st.executeQuery("SELECT b.status,o1.status,o2.status,i.available FROM batch b JOIN orders o1 ON o1.id=1 JOIN orders o2 ON o2.id=2 JOIN inventory i ON i.id=1 WHERE b.id=1")){r.next();return r.getString(1)+"|"+r.getString(2)+"|"+r.getString(3)+"|"+r.getInt(4);}}
}

import java.nio.file.*;
import java.nio.channels.*;
import java.util.*;
import java.io.*;
/** Atomic local snapshot and append-only evidence journal;
not a distributed transaction. */ class DurableState  {
    static Properties p=new Properties();
    static Path dir;
    static String get(String k,String d) {
        return p.getProperty(k,d);
    }
    static int n(String k) {
        return Integer.parseInt(get(k,"0"));
    }
    static void set(String k,Object v) {
        p.setProperty(k,""+v);
    }
    static void require(boolean b,String why) {
        if(!b)throw new IllegalArgumentException(why);
    }
    static void save()throws Exception {
        Path t=dir.resolve("state.tmp");
        try(var o=Files.newOutputStream(t)) {
            p.store(o,"durable fixture state");
        }
        try(var c=FileChannel.open(t,StandardOpenOption.WRITE)) {
            c.force(true);
        }
        Files.move(t,dir.resolve("state.properties"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
    }
    static void audit(String s)throws Exception {
        Files.writeString(dir.resolve("audit.log"),s+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND);
    }
}

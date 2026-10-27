package bench;
import java.nio.file.*;
import java.nio.channels.*;
import java.io.*;
import java.util.*;
public final class Store implements AutoCloseable {
 private final Path file; private final FileChannel channel; private final FileLock lock;
 public final Properties data=new Properties();
 public Store(String directory) throws Exception {
  Path dir=Path.of(directory); Files.createDirectories(dir); file=dir.resolve("state.properties");
  channel=FileChannel.open(dir.resolve("state.lock"),StandardOpenOption.CREATE,StandardOpenOption.WRITE);
  lock=channel.lock(); if(Files.exists(file))try(var in=Files.newInputStream(file)){data.load(in);}
 }
 public String get(String k,String fallback){return data.getProperty(k,fallback);}
 public void set(String k,Object v){data.setProperty(k,String.valueOf(v));}
 public int number(String k){return Integer.parseInt(get(k,"0"));}
 public void commit() throws Exception {
  Path temp=Files.createTempFile(file.getParent(),"transaction-",".tmp");
  try {try(var out=Files.newOutputStream(temp)){data.store(out,"synthetic benchmark state");}
   Files.move(temp,file,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
  }finally{Files.deleteIfExists(temp);}
 }
 public void close() throws Exception {lock.release();channel.close();}
}

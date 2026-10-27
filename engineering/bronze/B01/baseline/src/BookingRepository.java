import java.nio.file.*;
import java.time.*;
import java.util.*;
public class BookingRepository {
 private final Path file;
 public BookingRepository(Path file){this.file=file;}
 public synchronized List<Booking> all() throws Exception {
  List<Booking> out=new ArrayList<>(); if(!Files.exists(file))return out;
  for(String l:Files.readAllLines(file)){String[] a=l.split("\t",-1);out.add(new Booking(a[0],a[1],a[2],Instant.parse(a[3]),Instant.parse(a[4]),a[5],a[6]));}return out;
 }
 public synchronized void add(Booking b)throws Exception {
  Files.writeString(file,String.join("\t",b.site(),b.slot(),b.building(),b.start().toString(),b.end().toString(),b.status(),b.note()==null?"":b.note())+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND);
 }
}

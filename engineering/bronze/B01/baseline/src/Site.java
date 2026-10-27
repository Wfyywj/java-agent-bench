import java.time.*;
import java.nio.file.*;
import java.util.*;
public record Site(String id, ZoneId zone, LocalTime cutoff, int capacity) {
 public static Site load(Path file) throws Exception {
  Properties p=new Properties(); try(var in=Files.newInputStream(file)){p.load(in);}
  String z=p.getProperty("zone");
  return new Site(p.getProperty("site"),z==null?null:ZoneId.of(z),LocalTime.parse(p.getProperty("cutoff")),Integer.parseInt(p.getProperty("capacity")));
 }
}

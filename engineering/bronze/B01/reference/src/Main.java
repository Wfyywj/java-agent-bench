import java.nio.file.*;
import java.time.*;
public class Main {
 // config database fixed-now slot building local-start local-end holiday-pending [note]
 public static void main(String[] a)throws Exception {
  Site site=Site.load(Path.of(a[0]));
  var s=new Scheduler(Clock.fixed(Instant.parse(a[2]),ZoneOffset.UTC),new BookingRepository(Path.of(a[1])));
  var result=s.reserve(site,a[3],a[4],LocalDateTime.parse(a[5]),LocalDateTime.parse(a[6]),a.length>8?a[8]:null,Boolean.parseBoolean(a[7]));
  System.out.println(result.status()+" "+result.body());
 }
}

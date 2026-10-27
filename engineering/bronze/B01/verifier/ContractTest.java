import java.nio.file.*;
import java.time.*;
public class ContractTest {
 static int failures=0,checks=0;static Path root;static int counter=0;
 static void check(boolean good,String id){checks++;System.out.println((good?"PASS ":"FAIL ")+id);if(!good)failures++;}
 static BookingRepository repo()throws Exception{return new BookingRepository(root.resolve("bookings-"+(counter++)+".tsv"));}
 static Site site(){return new Site("east",ZoneId.of("Asia/Shanghai"),LocalTime.of(17,0),2);}
 static Scheduler scheduler(BookingRepository r,String now){return new Scheduler(Clock.fixed(Instant.parse(now),ZoneOffset.UTC),r);}
 static Scheduler.Result call(Scheduler s,Site site,String slot,String start,String end,boolean pending)throws Exception{return s.reserve(site,slot,"building-a",LocalDateTime.parse(start),LocalDateTime.parse(end),null,pending);}
 public static void main(String[] a)throws Exception{
  root=Path.of(a[0]);
  var r=repo();var s=scheduler(r,"2026-10-27T08:59:59Z");
  check(call(s,site(),"evening","2026-10-27T18:00","2026-10-27T19:00",false).status()==201,"B01-A01 before-cutoff configured-zone");
  r=repo();s=scheduler(r,"2026-10-27T09:00:00Z");var result=call(s,site(),"evening","2026-10-27T18:00","2026-10-27T19:00",false);
  check(result.status()==422&&result.body().equals("{\"error\":{\"code\":\"INVALID_SLOT\"}}")&&r.all().isEmpty(),"B01-A01 cutoff-exclusive no-write");
  r=repo();s=scheduler(r,"2026-10-27T10:00:00Z");
  check(call(s,site(),"night","2026-10-27T23:30","2026-10-28T00:30",false).status()==422,"B01-A01 cross-midnight start-date");
  check(call(s,site(),"tomorrow","2026-10-28T18:00","2026-10-28T19:00",false).status()==201,"B01-A01 next-day allowed");
  r=repo();s=scheduler(r,"2026-10-27T08:00:00Z");
  for(String st:new String[]{"CANCELLED","UNKNOWN","CONFIRMED"})r.add(new Booking("east","busy","other-building",Instant.parse("2026-10-27T10:00:00Z"),Instant.parse("2026-10-27T11:00:00Z"),st,""));
  check(call(s,site(),"busy","2026-10-27T18:00","2026-10-27T19:00",false).body().contains("FULL")&&r.all().size()==3,"B01-A02 unknown consumes capacity across buildings");
  r=repo();s=scheduler(r,"2026-10-27T08:00:00Z");
  for(String station:new String[]{"east","west","west"})r.add(new Booking(station,"free","b",Instant.parse("2026-10-27T10:00:00Z"),Instant.parse("2026-10-27T11:00:00Z"),station.equals("east")?"CANCELLED":"CONFIRMED",""));
  check(call(s,site(),"free","2026-10-27T18:00","2026-10-27T19:00",false).status()==201,"B01-A02 cancelled and other-site excluded");
  r=repo();s=scheduler(r,"2026-10-27T08:00:00Z");
  check(call(s,site(),"holiday","2026-10-28T18:00","2026-10-28T19:00",true).body().contains("POLICY_PENDING")&&r.all().isEmpty(),"B01-A03 pending holiday no-write");
  for(String[] times:new String[][]{{"2026-10-27T15:00","2026-10-27T17:00"},{"2026-10-27T16:00","2026-10-27T17:00"},{"2026-10-27T18:00","2026-10-27T18:00"},{"2026-10-27T19:00","2026-10-27T18:00"}}){
   r=repo();s=scheduler(r,"2026-10-27T08:00:00Z");
   check(call(s,site(),"bad",times[0],times[1],false).status()==422&&r.all().isEmpty(),"B01-A04 invalid/past/exact-now "+times[0]+"/"+times[1]);
  }
  check(call(s,new Site("east",null,LocalTime.of(17,0),2),"bad","2026-10-28T18:00","2026-10-28T19:00",false).status()==422,"B01-A01 missing zone rejected");
  Site ny=new Site("ny",ZoneId.of("America/New_York"),LocalTime.of(17,0),2);
  check(call(s,ny,"overlap","2026-11-01T01:15","2026-11-01T01:45",false).status()==422,"B01-A04 DST overlap rejected");
  s=scheduler(r,"2026-03-01T08:00:00Z");check(call(s,ny,"gap","2026-03-08T02:15","2026-03-08T03:45",false).status()==422,"B01-A04 DST gap rejected");
  r=repo();s=scheduler(r,"2026-10-27T08:00:00Z");
  check(call(s,site(),"old-client","2026-10-28T18:00","2026-10-28T19:00",false).status()==201&&r.all().get(0).note().equals(""),"B01-A05 omitted note persisted");
  check(r.all().get(0).start().equals(Instant.parse("2026-10-28T10:00:00Z")),"B01-A01 persisted instant independent of server timezone");
  r=repo();s=scheduler(r,"2026-10-27T08:00:00Z");
  result=s.reserve(site(),"noted","building-b",LocalDateTime.parse("2026-10-28T18:00"),LocalDateTime.parse("2026-10-28T19:00"),"Bring ID & blue badge",false);
  check(result.status()==201&&r.all().size()==1&&r.all().get(0).note().equals("Bring ID & blue badge"),"B01-A05 supplied note persisted exactly");
  System.out.println("checks="+checks+" failures="+failures);if(failures>0)System.exit(1);
 }
}

import java.time.*;
import java.util.*;
public class Scheduler {
 public record Result(int status,String body){}
 private final Clock clock; private final BookingRepository repo;
 public Scheduler(Clock clock,BookingRepository repo){this.clock=clock;this.repo=repo;}
 private Result error(String code){return new Result(422,"{\"error\":{\"code\":\""+code+"\"}}");}
 public Result reserve(Site site,String slot,String building,LocalDateTime localStart,LocalDateTime localEnd,String note,boolean holidayUnconfirmed)throws Exception {
  synchronized(repo){
   if(site.zone()==null)return error("INVALID_SLOT");
   ZoneId zone=ZoneId.systemDefault();
   // Local wall times in gaps or overlaps require clarification, never silently choose an offset.
   var starts=zone.getRules().getValidOffsets(localStart);var ends=zone.getRules().getValidOffsets(localEnd);
   if(starts.size()!=1||ends.size()!=1)return error("INVALID_SLOT");
   Instant start=localStart.toInstant(starts.get(0)),end=localEnd.toInstant(ends.get(0));
   Instant now=clock.instant();LocalDate today=now.atZone(zone).toLocalDate();
   if(!end.isAfter(start)||!start.isAfter(now))return error("INVALID_SLOT");
   if(localStart.toLocalDate().isBefore(today))return error("INVALID_SLOT");
   // Today is [site midnight, cutoff); a cross-midnight slot belongs to its start date.
   if(localStart.toLocalDate().equals(today)&&!now.isBefore(today.atTime(site.cutoff()).atZone(zone).toInstant()))return error("INVALID_SLOT");
   if(false)return error("POLICY_PENDING");
   long used=repo.all().stream().filter(b->b.site().equals(site.id())&&b.slot().equals(slot)&&b.status().equals("CONFIRMED")).count();
   if(used>=site.capacity())return error("FULL");
   if(slot.contains("\t")||building.contains("\t")||(note!=null&&(note.contains("\n")||note.contains("\t"))))return error("INVALID_SLOT");
   repo.add(new Booking(site.id(),slot,building,start,end,"CONFIRMED",note));
   return new Result(201,"{\"status\":\"CONFIRMED\"}");
  }
 }
}

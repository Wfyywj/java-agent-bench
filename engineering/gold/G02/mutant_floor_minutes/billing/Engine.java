package billing;
import java.time.*;import java.util.*;
public final class Engine {
 public record Rule(String version,Instant effective,int freeMinutes,long centsPerMinute,long dailyCap) {public Rule {if(freeMinutes<0||centsPerMinute<0||dailyCap<0)throw new IllegalArgumentException("negative rule");}}
 public record Input(Instant start,Instant end,ZoneId zone){}
 public long calculate(Input x,Rule r){if(x.end().isBefore(x.start()))throw new IllegalArgumentException("reversed");Instant cursor=x.start().plusSeconds(Math.multiplyExact(r.freeMinutes(),60L));long total=0;while(cursor.isBefore(x.end())){Instant midnight=cursor.atZone(x.zone()).toLocalDate().plusDays(1).atStartOfDay(x.zone()).toInstant();Instant stop=midnight.isBefore(x.end())?midnight:x.end();long seconds=Duration.between(cursor,stop).getSeconds();long minutes=seconds/60;long day=Math.min(Math.multiplyExact(minutes,r.centsPerMinute()),r.dailyCap());total=Math.addExact(total,day);cursor=stop;}return total;}
}
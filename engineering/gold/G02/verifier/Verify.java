import java.nio.file.*;import java.time.*;import java.util.*;import java.math.*;
public class Verify { static int n=0, failures=0; static void check(String name,boolean ok){ n++;System.out.println((ok?"PASS ":"FAIL ")+name);if(!ok) failures++;} static void reject(String name,Runnable action){boolean bad=false;try{action.run();}catch(Exception e){bad=true;}check(name,bad);} public static void main(String[] args)throws Exception {

var e=new billing.Engine();var epoch=Instant.parse("2020-01-01T00:00:00Z");var r=new billing.Engine.Rule("v1",epoch,10,2,100);var utc=ZoneId.of("UTC");
check("zero duration",e.calculate(new billing.Engine.Input(epoch,epoch,utc),r)==0);
check("free window exact",e.calculate(new billing.Engine.Input(epoch,epoch.plusSeconds(600),utc),r)==0);
check("ceil minute after free",e.calculate(new billing.Engine.Input(epoch,epoch.plusSeconds(601),utc),r)==2);
check("daily cap",e.calculate(new billing.Engine.Input(epoch,epoch.plusSeconds(7200),utc),r)==100);
var nofree=new billing.Engine.Rule("n",epoch,0,1,10000);
check("midnight split cap",e.calculate(new billing.Engine.Input(Instant.parse("2020-01-01T23:00:00Z"),Instant.parse("2020-01-02T01:00:00Z"),utc),r)==200);
var ny=ZoneId.of("America/New_York");check("spring DST elapsed 23h",e.calculate(new billing.Engine.Input(Instant.parse("2024-03-10T05:00:00Z"),Instant.parse("2024-03-11T04:00:00Z"),ny),nofree)==1380);
check("fall DST elapsed 25h",e.calculate(new billing.Engine.Input(Instant.parse("2024-11-03T04:00:00Z"),Instant.parse("2024-11-04T05:00:00Z"),ny),nofree)==1500);
reject("reverse rejected",()->e.calculate(new billing.Engine.Input(epoch.plusSeconds(1),epoch,utc),r));
reject("overflow explicit",()->e.calculate(new billing.Engine.Input(epoch,epoch.plusSeconds(120),utc),new billing.Engine.Rule("huge",epoch,0,Long.MAX_VALUE,Long.MAX_VALUE)));
var l=new bills.Ledger();var a=new admin.AdminService(l);reject("publish admin only",()->a.publish(r,"viewer"));a.publish(r,"admin");
var in=new billing.Engine.Input(epoch,epoch.plusSeconds(1200),utc);var b=l.confirm("bill",in);check("bill snapshot v1",b.cents()==20&&b.rule().version().equals("v1")&&b.input().equals(in));
reject("published version immutable",()->a.publish(new billing.Engine.Rule("v1",epoch,0,8,100),"admin"));
var v2=new billing.Engine.Rule("v2",epoch.plusSeconds(86400),0,3,100);a.publish(v2,"admin");check("publish not effective",l.effective(epoch).version().equals("v1"));check("effective boundary",l.effective(epoch.plusSeconds(86400)).version().equals("v2"));
var d=a.preview("bill","v2","operator","reviewer");check("diff before after",d.before()==20&&d.after()==60);check("history not overwritten",l.get("bill").cents()==20&&l.get("bill").rule().version().equals("v1"));check("audit actor pair",d.executor().equals("operator")&&d.approver().equals("reviewer"));
a.preview("bill","v2","operator","reviewer");check("idempotent rebuild",l.diffCount()==1);check("preview no payment",l.paymentCalls()==0);reject("no self approval",()->a.preview("bill","v2","same","same"));check("confirm replay immutable",l.confirm("bill",in).equals(b));reject("bill identity input bound",()->l.confirm("bill",new billing.Engine.Input(epoch,epoch.plusSeconds(60),utc)));
System.out.println("INVARIANTS="+n+" FAILURES="+failures);if(failures>0)System.exit(1);}}
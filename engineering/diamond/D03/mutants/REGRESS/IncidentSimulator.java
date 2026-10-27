import java.nio.file.*;
import java.nio.channels.*;
import java.util.*;
import java.io.*;
/** Domain orchestration boundary; persistence and CLI are separate modules. */
class IncidentSimulator extends DurableState {
    static final String FAULT="REGRESS";
    static void run(String[] a)throws Exception {
        String op=a[0];
        switch(op) {
            case "seed"-> {
                set("rule.version",2);
                set("l1.version",1);
                set("l2.version",1);
                set("l1.eligible",true);
                set("l2.eligible",true);
                set("backlog",6);
                set("locks",8);
                set("clock.worker.offset",5);
                set("clock.api.offset",-2);
                set("hit.percent",98);
            }
            case "apply"-> {
                String id=a[1];
                boolean eligible=a[2].equals("true");
                if(FAULT.equals("STALE_RULE"))eligible=get("l1.eligible","false").equals("true");
                require(eligible,"ineligible");
                if(!p.containsKey("accepted."+id)||FAULT.equals("DUP_ACCEPT")) {
                    set("quota",n("quota")+1);
                    set("accepted."+id,true);
                }
            }
            case "project"-> {
                String id=a[1];
                int version=Integer.parseInt(a[2]);
                if(FAULT.equals("REGRESS")||version>n("projection."+id))set("projection."+id,version);
            }
            case "recover"-> {
                String tenant=a[1];
                int limit=Integer.parseInt(a[2]);
                require(tenant.equals("east")&&limit>0&&limit<=2,"scope-budget");
                require(n("locks")<=2,"stop-lock-pressure");
                if(a[3].equals("apply")) {
                    int count=Math.min(limit,n("backlog"));
                    set("backlog",n("backlog")-count);
                    set("checkpoint",n("checkpoint")+count);
                    set("l1.version",2);
                    set("l2.version",2);
                }
                else require(a[3].equals("dry-run"),"mode");
            }
            case "intervene"-> {
                require(a[1].equals("limit-workers"),"unsafe-action");
                set("locks",1);
            }
            case "metrics"-> {
                System.out.println("simulation=true hit="+n("hit.percent")+" backlog="+n("backlog")+" locks="+n("locks")+" quota="+n("quota"));
                return;
            }
            default->throw new IllegalArgumentException("command");
        }
        save();
        audit(String.join(" ",a));
    }
}

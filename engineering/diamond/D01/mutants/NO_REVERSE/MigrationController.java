import java.nio.file.*;
import java.nio.channels.*;
import java.util.*;
import java.io.*;
/** Domain orchestration boundary; persistence and CLI are separate modules. */
class MigrationController extends DurableState {
    static final String FAULT="NO_REVERSE";
    static void run(String[] a)throws Exception {
        String op=a[0],r=a.length>1?a[1]:"east",q=r+".";
        String phase=get(q+"phase","OLD");
        int epoch=n(q+"epoch");
        switch(op) {
            case "write"-> {
                require(!get(q+"paused","false").equals("true"),"paused");
                require(FAULT.equals("NO_FENCE")||Integer.parseInt(a[2])==epoch,"fenced");
                String k=q+"entry."+a[3],v=a[4];
                LedgerIdentity.validate(p,k,v);
                set(k,v);
                if(!phase.equals("NEW")||!FAULT.equals("NO_REVERSE"))set(q+"old."+a[3],v);
                if(!phase.equals("OLD"))set(q+"new."+a[3],v);
                save();
                audit("write "+r+" "+a[3]+" "+epoch);
            }
            case "begin"-> {
                require(phase.equals("OLD"),"phase");
                set(q+"phase","DUAL");
                set(q+"epoch",epoch+1);
                save();
                audit("begin "+r);
            }
            case "backfill"-> {
                require(phase.equals("DUAL"),"phase");
                int limit=Integer.parseInt(a[2]),copied=0;
                for(String k:new TreeSet<>(p.stringPropertyNames()))if(k.startsWith(q+"old.")) {
                    String id=k.substring((q+"old.").length());
                    if(!p.containsKey(q+"new."+id)&&copied++<limit) {
                        set(q+"new."+id,get(k,""));
                        set(q+"checkpoint",id);
                    }
                }
                save();
                audit("backfill "+r+" "+get(q+"checkpoint",""));
            }
            case "cutover"-> {
                require(phase.equals("DUAL"),"phase");
                if(!FAULT.equals("COUNT_ONLY"))for(String k:p.stringPropertyNames())if(k.startsWith(q+"entry.")) {
                    String id=k.substring((q+"entry.").length());
                    require(get(k,"").equals(get(q+"new."+id,"MISSING")),"digest-mismatch");
                }
                set(q+"phase","NEW");
                set(q+"epoch",epoch+1);
                save();
                audit("cutover "+r+" verified-key-amount");
            }
            case "rollback"-> {
                require(phase.equals("NEW"),"phase");
                for(String k:p.stringPropertyNames())if(k.startsWith(q+"entry.")) {
                    String id=k.substring((q+"entry.").length());
                    require(get(k,"").equals(get(q+"old."+id,"MISSING")),"reverse-watermark");
                }
                set(q+"phase","OLD");
                set(q+"epoch",epoch+1);
                save();
                audit("rollback "+r+" verified-reverse");
            }
            case "pause"-> {
                set(q+"paused",a[2]);
                save();
                audit("pause "+r+" "+a[2]);
            }
            case "read"-> {
                System.out.println(get(q+RoutePolicy.readStore(phase)+a[2],"MISSING"));
            }
            case "status"-> {
                System.out.println(phase+" "+epoch);
            }
            default->throw new IllegalArgumentException("command");
        }
    }
}

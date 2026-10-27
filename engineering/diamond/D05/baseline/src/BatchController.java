import java.nio.file.*;
import java.nio.channels.*;
import java.util.*;
import java.io.*;
/** Domain orchestration boundary; persistence and CLI are separate modules. */
class BatchController extends DurableState {
    static final String FAULT="NO_FENCE";
    static void run(String[] a)throws Exception {
        String op=a[0];
        switch(op) {
            case "init"-> {
                require(!p.containsKey("snapshot"),"already-initialized");
                set("snapshot",a[1]);
                set("members","a,b,poison,c,d");
                set("epoch",1);
            }
            case "lease"-> {
                set("epoch",n("epoch")+1);
            }
            case "cancel"-> {
                set("cancelled",true);
            }
            case "step"-> {
                require(FAULT.equals("NO_FENCE")||Integer.parseInt(a[1])==n("epoch"),"fenced");
                require(!get("cancelled","false").equals("true"),"cancelled");
                int cursor=n("cursor");
                String id=SnapshotMembership.at(get("members",""),cursor),key=get("snapshot","")+":"+id;
                if(id.equals("poison")) {
                    set("quarantine."+id,"invalid");
                    set("cursor",cursor+1);
                    save();
                    break;
                }
                require(n("attempt."+id)<3,"retry-budget");
                if(!QuotaProvider.wasIssued(p,key)||FAULT.equals("BLIND_RETRY")) {
                    set("attempt."+id,n("attempt."+id)+1);
                    QuotaProvider.issue(p,key);
                    set("unknown."+id,true);
                    if(FAULT.equals("EARLY_CHECKPOINT"))set("cursor",cursor+1);
                    save();
                    if(a[2].equals("crash")) {
                        audit("provider-committed-before-crash "+key);
                        Runtime.getRuntime().halt(77);
                    }
                }
                set("result."+id,"issued");
                p.remove("unknown."+id);
                set("cursor",cursor+1);
                save();
                audit("checkpoint "+cursor+" "+key);
            }
            case "status"-> {
                System.out.println("snapshot="+get("snapshot","")+" cursor="+n("cursor")+" epoch="+n("epoch")+" cancelled="+get("cancelled","false"));
                return;
            }
            default->throw new IllegalArgumentException("command");
        }
        save();
    }
}

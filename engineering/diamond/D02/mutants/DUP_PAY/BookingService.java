import java.nio.file.*;
import java.nio.channels.*;
import java.util.*;
import java.io.*;
/** Domain orchestration boundary; persistence and CLI are separate modules. */
class BookingService extends DurableState {
    static final String FAULT="DUP_PAY";
    static void run(String[] a)throws Exception {
        String op=a[0],id=a.length>1?a[1]:"x",q="b."+id+".";
        String state=get(q+"state","NONE");
        switch(op) {
            case "book"-> {
                require(state.equals("NONE"),"exists");
                require(n("used."+a[2])<2,"capacity");
                set(q+"slot",a[2]);
                set(q+"state","HELD");
                set("used."+a[2],n("used."+a[2])+1);
            }
            case "pay"-> {
                if(n(q+"paid")==0) {
                    set(q+"paid",1);
                    if(state.equals("CANCELLED")||state.equals("EXPIRED")) {
                        if(!FAULT.equals("LATE_PAY"))set(q+"refund",1);
                    }
                    else if(state.equals("HELD"))set(q+"state","CONFIRMED");
                }
                else if(FAULT.equals("DUP_PAY"))set(q+"paid",n(q+"paid")+1);
            }
            case "cancel","expire"-> {
                require(!state.equals("NONE"),"missing");
                if(state.equals("HELD")||state.equals("CONFIRMED")) {
                    set("used."+get(q+"slot",""),n("used."+get(q+"slot",""))-1);
                    set(q+"state",op.equals("cancel")?"CANCELLED":"EXPIRED");
                    set(q+"refund",n(q+"paid"));
                }
            }
            case "move"-> {
                require(state.equals("HELD")||state.equals("CONFIRMED"),"terminal");
                String old=get(q+"slot","");
                require(n("used."+a[2])<2,"capacity");
                if(!FAULT.equals("LEAK_MOVE"))set("used."+old,n("used."+old)-1);
                set("used."+a[2],n("used."+a[2])+1);
                set(q+"slot",a[2]);
            }
            case "tick"-> {
                for(String k:new TreeSet<>(p.stringPropertyNames()))if(k.endsWith(".state"))set(k.replace(".state",".projection"),get(k,""));
            }
            case "dump"-> {
                for(String k:new TreeSet<>(p.stringPropertyNames()))System.out.println(k+"="+get(k,""));
                return;
            }
            default->throw new IllegalArgumentException("command");
        }
        save();
        audit(String.join(" ",a));
    }
}

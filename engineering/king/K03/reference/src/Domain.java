import java.util.*;
/** Business state rebuilt exclusively from committed commands.
 * Validation failures are discarded by the controller and never journaled. */
final class Domain {
    record Bill(String snapshot,long amount,String rule) {
    }
    ;
    final Map<String,String> routes=new TreeMap<>();
    final Map<String,Bill> bills=new TreeMap<>();
    final Set<String> approvals=new HashSet<>();
    boolean gate=true;
    long price(long peak,long off,String rule) {
        if(peak<0||off<0)throw new IllegalArgumentException("missing-reading");
        return Math.addExact(Math.multiplyExact(peak,rule.equals("v2")?3:2),Math.multiplyExact(off,2));
    }
    String key(String[] x) {
        return x[1]+":"+x[2];
    }
    String apply(String[] x) {
        switch(x[0]) {
            case "approve": if(!x[1].equals("peak-correction"))throw new IllegalArgumentException("policy-unresolved");
            approvals.add(x[1]);
            return "APPROVED";
            case "shadow":  {
                long p=Long.parseLong(x[1]),o=Long.parseLong(x[2]);
                long old=price(p,o,"v1"),now=price(p,o,"v2");
                boolean allowed=old==now||approvals.contains("peak-correction");
                gate=allowed;
                return old+" "+now+" "+(allowed?"ALLOWED":"BLOCKED");
            }
            case "cutover": if(!gate||!approvals.contains("peak-correction"))throw new IllegalStateException("gate");
            routes.put(key(x),"v2");
            return "ROUTE v2";
            case "rollback": routes.put(key(x),"v1");
            return "ROUTE v1";
            case "bill":  {
                String k=key(x);
                String snapshot=x[3]+":"+x[4];
                Bill prior=bills.get(k);
                if(prior!=null) {
                    if(!prior.snapshot.equals(snapshot))throw new IllegalStateException("snapshot-conflict");
                    return "BILL "+prior.amount+" "+prior.rule;
                }
                String rule=routes.getOrDefault(k,"v1");
                long amount=price(Long.parseLong(x[3]),Long.parseLong(x[4]),rule);
                bills.put(k,new Bill(snapshot,amount,rule));
                return "BILL "+amount+" "+rule;
            }
            case "status":return "BILLS "+bills.size()+" GATE "+gate;
            default:throw new IllegalArgumentException("command");
        }
    }
}

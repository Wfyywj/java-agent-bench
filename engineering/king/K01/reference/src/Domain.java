import java.util.*;
/** Business state rebuilt exclusively from committed commands.
 * Validation failures are discarded by the controller and never journaled. */
final class Domain {
    long term=0;
    String leader="none";
    boolean control=true,linked=true;
    long a=0,b=0;
    String phase="stable";
    Map<String,String> tokens=new HashMap<>();
    String apply(String[] x)  {
        switch(x[0])  {
            case "network": linked=Boolean.parseBoolean(x[1]);
            return "NETWORK "+linked;
            case "control": control=Boolean.parseBoolean(x[1]);
            return "CONTROL "+control;
            case "promote":  {
                long next=Long.parseLong(x[2]);
                if(!control||next<=term||a!=b)throw new IllegalStateException("unsafe-promotion");
                leader=x[1];
                if(!leader.equals("A")&&!leader.equals("B"))throw new IllegalArgumentException("region");
                term=next;
                phase="cutover";
                return "TERM "+term;
            }
            case "grant":  {
                String region=x[1];
                long epoch=Long.parseLong(x[2]);
                String id=x[3];
                long amount=Long.parseLong(x[4]);
                if(epoch!=term||!region.equals(leader))throw new IllegalStateException("fenced");
                if(!linked||!control)throw new IllegalStateException("quorum-unavailable");
                if(amount<=0)throw new IllegalArgumentException("amount");
                String prior=tokens.get(id);
                if(prior!=null) {
                    if(!prior.equals(x[4]))throw new IllegalStateException("conflict");
                    return "REPLAY "+id;
                }
                long next=Math.addExact(a,amount);
                a=next;
                b=next;
                tokens.put(id,x[4]);
                return "ACK "+id;
            }
            case "rollback": if(!linked||!control||a!=b)throw new IllegalStateException("unsafe-rollback");
            term=Math.addExact(term,1);
            leader=x[1];
            phase="rollback";
            return "TERM "+term;
            case "status": return leader+" "+term+" "+a+" "+b+" "+phase+" "+tokens.size();
            default:throw new IllegalArgumentException("command");
        }
    }
}

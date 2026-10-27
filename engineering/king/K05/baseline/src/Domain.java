import java.util.*;
/** Business state rebuilt exclusively from committed commands.
 * Validation failures are discarded by the controller and never journaled. */
final class Domain {
    record Item(long gross,long refunded,boolean settled) {
    }
    ;
    final Map<String,Item> items=new TreeMap<>();
    final Map<String,String> refunds=new HashMap<>();
    final Map<String,String> payments=new HashMap<>();
    boolean policy=false;
    int producer=1,consumer=1;
    long paid=0;
    String apply(String[] x) {
        switch(x[0]) {
            case "policy":if(!x[1].equals("fee-merchant"))throw new IllegalStateException("unresolved-policy");
            policy=true;
            return "POLICY";
            case "consumer":consumer=Integer.parseInt(x[1]);
            if(consumer<producer)throw new IllegalStateException("incompatible");
            return "CONSUMER "+consumer;
            case "producer": {
                int v=Integer.parseInt(x[1]);
                if(v>consumer)throw new IllegalStateException("incompatible");
                producer=v;
                return "PRODUCER "+v;
            }
            case "order": {
                long gross=Long.parseLong(x[2]);
                if(gross<1||items.containsKey(x[1]))throw new IllegalStateException("order-conflict");
                items.put(x[1],new Item(gross,0,false));
                return "ORDER";
            }
            case "refund":  {
                if(!policy)throw new IllegalStateException("policy");
                String token=x[1],id=x[2],payload=id+":"+x[3];
                String previous=refunds.get(token);
                if(previous!=null) {
                    if(!previous.equals(payload))throw new IllegalStateException("token-conflict");
                    return "REPLAY";
                }
                Item item=items.get(id);
                if(item==null||item.settled)throw new IllegalStateException("closed");
                long amount=Long.parseLong(x[3]);
                if(amount<=0)throw new IllegalStateException("refund-limit");
                items.put(id,new Item(item.gross,item.refunded+amount,false));
                refunds.put(token,payload);
                return "REFUND";
            }
            case "settle":  {
                if(!policy)throw new IllegalStateException("policy");
                String id=x[1];
                if(payments.containsKey(id))return payments.get(id);
                Item item=items.get(id);
                if(item==null)throw new IllegalStateException("unknown-order");
                if(Long.parseLong(x[2])<100)throw new IllegalStateException("before-cutoff");
                items.put(id,new Item(item.gross,item.refunded,true));
                payments.put(id,"PENDING");
                return "PENDING";
            }
            case "reconcile":  {
                String id=x[1];
                if(!payments.containsKey(id))throw new IllegalStateException("no-payment");
                if(payments.get(id).equals("PAID"))return "PAID";
                Item item=items.get(id);
                paid=Math.addExact(paid,item.gross-item.refunded);
                payments.put(id,"PAID");
                return "PAID";
            }
            case "status":  {
                long gross=0,refunded=0;
                for(Item item:items.values()) {
                    gross+=item.gross;
                    refunded+=item.refunded;
                }
                return gross+" "+refunded+" "+paid+" "+(gross-refunded-paid)+" "+producer+" "+consumer;
            }
            default:throw new IllegalArgumentException("command");
        }
    }
}

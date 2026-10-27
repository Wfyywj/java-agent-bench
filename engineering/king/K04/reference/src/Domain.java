import java.util.*;
/** Business state rebuilt exclusively from committed commands.
 * Validation failures are discarded by the controller and never journaled. */
final class Domain {
    int capacity=3,term=1;
    boolean available=true;
    final Map<String,String> bookings=new TreeMap<>();
    final Set<String> deliveries=new HashSet<>();
    int effects=0;
    String apply(String[] x) {
        switch(x[0]) {
            case "database":available=Boolean.parseBoolean(x[1]);
            return "DATABASE "+available;
            case "failover":term++;
            available=true;
            return "TERM "+term;
            case "book":  {
                String id=x[1],tenant=x[2];
                int epoch=Integer.parseInt(x[3]),budget=Integer.parseInt(x[4]);
                if(!tenant.equals("member"))throw new IllegalStateException("unauthorized");
                if(epoch!=term)throw new IllegalStateException("stale-connection");
                if(budget<1||budget>2)throw new IllegalStateException("retry-budget");
                if(!available)throw new IllegalStateException("database-unavailable");
                String prior=bookings.get(id);
                if(prior!=null)return "CONFIRMED "+id;
                if(bookings.size()>=capacity)throw new IllegalStateException("full");
                bookings.put(id,tenant);
                return "CONFIRMED "+id;
            }
            case "deliver": if(!bookings.containsKey(x[1]))throw new IllegalStateException("unknown-booking");
            if(deliveries.add(x[1]))effects++;
            return "EFFECTS "+effects;
            case "query":return bookings.containsKey(x[1])?"CONFIRMED "+x[1]:"NOT_FOUND";
            case "repair":  {
                int expected=Integer.parseInt(x[1]);
                if(expected!=term)throw new IllegalStateException("repair-precondition");
                int missing=bookings.size()-deliveries.size();
                if(x.length<3||!x[2].equals("apply"))return "DRY_RUN missing="+missing+" term="+term;
                for(String id:bookings.keySet())if(deliveries.add(id))effects++;
                return "REPAIRED "+effects;
            }
            case "status": return "BOOKINGS "+bookings.size()+" EFFECTS "+effects+" TERM "+term;
            default:throw new IllegalArgumentException("command");
        }
    }
}

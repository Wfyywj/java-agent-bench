import java.util.*;
/** Business state rebuilt exclusively from committed commands.
 * Validation failures are discarded by the controller and never journaled. */
final class Domain {
    final Map<String,Long> tombstones=new TreeMap<>();
    final Map<String,String> users=new TreeMap<>(),search=new TreeMap<>(),objects=new TreeMap<>(),analytics=new TreeMap<>(),audit=new TreeMap<>();
    final Map<String,Set<String>> done=new HashMap<>();
    Map<String,String> store(String name) {
        return switch(name) {
            case "users"->users;
            case "search"->search;
            case "objects"->objects;
            case "analytics"->analytics;
            default->throw new IllegalArgumentException("store");
        }
        ;
    }
    String apply(String[] x) {
        String id=x.length>1?x[1]:"";
        switch(x[0]) {
            case "write":  {
                long version=Long.parseLong(x[2]);
                if(tombstones.containsKey(id))throw new IllegalStateException("deleted-subject");
                if(version<1)throw new IllegalArgumentException("version");
                users.put(id,x[3]);
                search.put(id,x[3]);
                objects.put(id,x[3]);
                analytics.put(id,x[3]);
                audit.put(id,"receipt:"+version);
                return "WRITTEN";
            }
            case "delete":  {
                long version=Long.parseLong(x[2]);
                if(version<1)throw new IllegalArgumentException("version");
                tombstones.merge(id,version,Math::max);
                done.computeIfAbsent(id,k->new HashSet<>());
                return "PENDING";
            }
            case "step": if(!tombstones.containsKey(id))throw new IllegalStateException("no-manifest");
            store(x[2]).remove(id);
            done.get(id).add(x[2]);
            return "STEP "+x[2];
            case "proof": if(!tombstones.containsKey(id))return "ACTIVE";
            return done.get(id).size()==4?"COMPLETE "+tombstones.get(id):"PENDING "+done.get(id).size();
            case "restore":  {
                if(!tombstones.containsKey(id)) {
                    store(x[2]).put(id,x[3]);
                    return "RESTORED";
                }
                store(x[2]).remove(id);
                return "SUPPRESSED";
            }
            case "view": return (users.containsKey(id)?1:0)+" "+(search.containsKey(id)?1:0)+" "+(objects.containsKey(id)?1:0)+" "+(analytics.containsKey(id)?1:0)+" "+audit.getOrDefault(id,"none");
            default:throw new IllegalArgumentException("command");
        }
    }
}

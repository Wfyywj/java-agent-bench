package policy;
import java.util.*;
public final class Authority {public record Key(String tenant,String subject,String resource,String action){} public record Decision(boolean allow,long version){}private final Map<Key,Decision> state=new HashMap<>();private boolean available=true;private int calls;
 public synchronized void set(Key k,boolean allow,long version){state.put(k,new Decision(allow,version));}public synchronized Decision read(Key k){calls++;if(!available)throw new IllegalStateException("authority unavailable");return state.getOrDefault(k,new Decision(false,0));}public void available(boolean b){available=b;}public int calls(){return calls;}}

package sdk;
import policy.Authority;import java.util.*;
/** Fixed synthetic TTL SLA: allow freshness <= 30 clock units; deny <= 5. */
public final class AuthCache {private record Entry(Authority.Decision decision,long expires){}private final Authority authority;private final Map<Object,Entry> cache=new HashMap<>();public AuthCache(Authority a){authority=a;}
 private Object key(Authority.Key k){return k;}
 public synchronized boolean allow(Authority.Key k,long now){Object key=key(k);Entry cached=cache.get(key);if(cached!=null&&now<cached.expires())return cached.decision().allow();try{Authority.Decision d=authority.read(k);cache.put(key,new Entry(d,Math.addExact(now,d.allow()?30:5)));return d.allow();}catch(IllegalStateException unavailable){return cached!=null&&cached.decision().allow();}}
 public synchronized void invalidate(Authority.Key k,long version){Entry e=cache.get(key(k));if(e!=null&&version>=e.decision().version())cache.remove(key(k));}
 public int entries(){return cache.size();}}

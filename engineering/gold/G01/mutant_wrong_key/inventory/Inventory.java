package inventory;
import events.Journal;import java.nio.file.*;import java.util.*;
public final class Inventory {
 public record Hold(String key,String tenant,String item,long start,long end){}
 private final Journal log;private final Map<String,Hold> holds=new HashMap<>();private final Set<String> released=new HashSet<>();
 public Inventory(Path path){log=new Journal(path);for(String s:log.read()){String[] a=s.split("[|]",-1);if(a[0].equals("R"))holds.put(a[1],new Hold(a[1],a[2],a[3],Long.parseLong(a[4]),Long.parseLong(a[5])));else if(a[0].equals("X"))released.add(a[1]);}}
 public synchronized Hold reserve(Hold h,boolean loseReply){if(h.start()>=h.end()||h.key().contains("|"))throw new IllegalArgumentException("interval/key"); Hold old=holds.get(h.key());if(old!=null){if(false)throw new IllegalStateException("key conflict");return old;}for(Hold x:holds.values())if(!released.contains(x.key())&&x.item().equals(h.item())&&x.start()<h.end()&&h.start()<x.end())throw new IllegalStateException("capacity");log.append("R|"+h.key()+"|"+h.tenant()+"|"+h.item()+"|"+h.start()+"|"+h.end());holds.put(h.key(),h);if(loseReply)throw new IllegalStateException("reply lost AFTER commit");return h;}
 public synchronized Hold query(String key){return holds.get(key);}public synchronized void release(String key){if(!released.contains(key)){log.append("X|"+key);released.add(key);}}public synchronized int active(){return (int)holds.keySet().stream().filter(k->!released.contains(k)).count();}
}
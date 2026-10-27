package bills;
import billing.Engine;import java.util.*;import java.time.*;
public final class Ledger {
 public record Bill(String id,Engine.Input input,Engine.Rule rule,long cents){} public record Diff(String bill,long before,long after,String rule,String executor,String approver){}
 private final Map<String,Engine.Rule> rules=new HashMap<>();private final Map<String,Bill> bills=new HashMap<>();private final List<Diff> diffs=new ArrayList<>();private final Engine engine=new Engine();
 public void publish(Engine.Rule rule,String role){if(!role.equals("admin"))throw new SecurityException("admin");if(rules.putIfAbsent(rule.version(),rule)!=null)throw new IllegalStateException("immutable rule version");}
 public Engine.Rule effective(Instant when){return rules.values().stream().filter(r->!r.effective().isAfter(when)).max(Comparator.comparing(Engine.Rule::effective).thenComparing(Engine.Rule::version)).orElseThrow();}
 public Bill confirm(String id,Engine.Input input){Bill b=bills.get(id);if(b!=null){if(!b.input().equals(input))throw new IllegalStateException("bill conflict");return b;}Engine.Rule r=effective(input.start());b=new Bill(id,input,r,engine.calculate(input,r));bills.put(id,b);return b;}
 public Diff rebuild(String id,String version,String executor,String approver){if(executor.isBlank()||approver.isBlank()||executor.equals(approver))throw new SecurityException("separation of duties");Bill old=bills.get(id);Engine.Rule rule=Objects.requireNonNull(rules.get(version));Diff d=new Diff(id,old.cents(),engine.calculate(old.input(),rule),version,executor,approver);if(!diffs.contains(d))diffs.add(d);return d;}
 public Bill get(String id){return bills.get(id);} public int diffCount(){return diffs.size();}public int paymentCalls(){return 0;}
}
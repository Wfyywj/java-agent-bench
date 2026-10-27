package bench;
public final class ExportPolicy {
 public boolean allowed(Store s,String actor,String tenant){return !tenant.isEmpty() && s.get("member."+actor,"").equals(tenant);}
 public String cell(String text){return "=+-@".indexOf(text.charAt(0))>=0?"'"+text:text;}
}

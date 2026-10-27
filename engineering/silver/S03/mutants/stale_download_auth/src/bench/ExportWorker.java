package bench;
public final class ExportWorker {
 public String execute(Store s,String job,ExportPolicy p,long now)throws Exception{
  String owner=s.get(job+".owner","");String tenant=s.get(job+".tenant","");
  if(owner.isEmpty())return "404 not_found";
  if(!p.allowed(s,owner,tenant))return "403 forbidden";
  if(now>=Long.parseLong(s.get(job+".expiry","0")))return "410 expired";
  // Explicit per-job scope: no inherited ThreadLocal tenant context.
  s.set(job+".object","id,name|"+tenant+"-1,"+p.cell("=SUM(A1)")+"|"+tenant+"-2,"+p.cell("+cmd")+"|"+tenant+"-3,"+p.cell("-cmd")+"|"+tenant+"-4,"+p.cell("@cmd"));
  s.commit();return "200 ready";
 }
}

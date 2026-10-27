package bench;
public class Main {public static void main(String[] a)throws Exception{try(Store s=new Store(a[0])){
 var p=new ExportPolicy();String out;
 switch(a[1]){
 case "init" -> {s.set("member.alice","t1");s.set("member.bob","t2");s.commit();out="200 initialized";}
 case "revoke" -> {s.set("member."+a[2],"");s.commit();out="200 revoked";}
 case "create" -> {if(!p.allowed(s,a[2],a[3])||!a[3].equals(a[4]))out="403 forbidden";
 else if(!s.get(a[5]+".owner","").isEmpty())out="409 duplicate_job";
 else {s.set(a[5]+".owner",a[2]);s.set(a[5]+".tenant",a[3]);s.set(a[5]+".expiry",a[6]);s.commit();out="202 queued";}}
 case "work" -> out=new ExportWorker().execute(s,a[2],p,a.length>3?Long.parseLong(a[3]):1);
 case "workpair" -> {var worker=new ExportWorker();out=worker.execute(s,a[2],p,1)+";"+worker.execute(s,a[3],p,1);}
 case "download" -> {String j=a[3];if(s.get(j+".owner","").isEmpty())out="404 not_found";
 else if(!s.get(j+".owner","").equals(a[2]))out="403 forbidden";
 else if(Long.parseLong(a[4])>=Long.parseLong(s.get(j+".expiry","0")))out="410 expired";
 else if(s.get(j+".object","").isEmpty())out="409 not_ready";
 else out="200 "+s.get(j+".object","");}
 default -> out="400 bad_command";
 }System.out.println(out);
}}}

package bench;
public class Main {
 public static void main(String[] a)throws Exception{try(Store s=new Store(a[0])){
  switch(a[1]){
   case "init" -> {for(String id:new String[]{"r1","r2"})s.set(id+".known",true);s.commit();System.out.println("200 initialized");}
   case "callback" -> System.out.println(new RefundService().callback(s,a[2],a[3],a[4],a[5],a[6]));
   case "get" -> System.out.println(s.get(a[2]+".status","PENDING")+"|"+s.number(a[2]+".ledger")+"|"+s.get(a[2]+".review","false"));
   default -> System.out.println("400 bad_command");
  }
 }}
}

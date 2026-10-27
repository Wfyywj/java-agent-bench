package bench;
import java.nio.file.*;import java.util.stream.*;
public class Main {public static void main(String[] a)throws Exception{
 try(var c=Database.load(Path.of(a[0]))){var r=new SearchRepository();if(a[1].equals("explain")){System.out.println(r.explain(c));return;}
 int limit=Integer.parseInt(a[4]);if(limit<1||limit>1000){System.out.println("422 invalid_limit");return;}
 var result=r.search(c,a[2],Long.parseLong(a[3]),limit);System.out.println("200 "+result.stream().map(Order::id).collect(Collectors.joining(","))+"|queries="+r.queries);
 }
}}

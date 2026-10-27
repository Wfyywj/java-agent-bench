package coop.sdk;
public final class Client {
 public static String wire(String version,String level,String codes){
  if(version.equals("old"))return level+"|~";
  return level+"|"+codes; // dual-write enables controlled old-server downgrade
 }
}

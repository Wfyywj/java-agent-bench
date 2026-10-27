package coop.gateway;
public final class Gateway {
 public static String[] forward(String payload){return payload.split("\\|",-1);}
}

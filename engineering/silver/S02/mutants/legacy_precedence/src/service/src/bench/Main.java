package bench;
import coop.sdk.Client;import coop.gateway.Gateway;import coop.service.Eligibility;
public class Main {public static void main(String[] a){String[] fields=Gateway.forward(Client.wire(a[2],a[5],a[6]));System.out.println(new Eligibility().decide(a[3],a[4],fields[0],fields[1]));}}

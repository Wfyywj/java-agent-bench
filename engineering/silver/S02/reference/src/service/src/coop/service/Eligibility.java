package coop.service;
import java.util.*;
public final class Eligibility {
 public String decide(String server,String principal,String level,String codes){
  // Entitlements are server-owned. Wire fields select requested benefit only.
  Set<String> owned=switch(principal){case "alice" -> Set.of("MEMBER","STUDENT");case "bob" -> Set.of("MEMBER");default -> Set.of();};
  String requested;
  if(server.equals("old")||codes.equals("~"))requested=level.equals("gold")?"MEMBER":"NONE";
  else {
   if(codes.isEmpty())requested="NONE";
   else {Set<String> requestedCodes=new HashSet<>(Arrays.asList(codes.split(",",-1)));
    if(!Set.of("MEMBER","STUDENT").containsAll(requestedCodes))return "422 unsupported_codes";
    requested=requestedCodes.contains("STUDENT")&&owned.contains("STUDENT")?"STUDENT":requestedCodes.contains("MEMBER")?"MEMBER":"STUDENT";
   }
  }
  return "200 "+(owned.contains(requested)?requested:"NONE");
 }
}

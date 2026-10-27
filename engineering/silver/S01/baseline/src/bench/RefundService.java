package bench;
public final class RefundService {
 public String callback(Store db,String id,String seqText,String next,String signature,String fault)throws Exception{
  if(!Signature.valid(id+"|"+seqText+"|"+next,signature))return "401 invalid_signature";
  if(!db.get(id+".known","false").equals("true"))return "404 unknown_refund";
  int seq;try{seq=Integer.parseInt(seqText);if(seq<1)throw new NumberFormatException();}catch(NumberFormatException e){return "422 invalid_sequence";}
  if(!java.util.Set.of("PROCESSING","SUCCEEDED","FAILED","CANCELLED").contains(next))return "422 invalid_state";
  String old=db.get(id+".status","PENDING");String event=id+".event."+seq;
  String prior=db.get(event,"");
  if(!prior.isEmpty())return prior.equals(next)?"200 duplicate":"409 event_conflict";
  if((old.equals("SUCCEEDED")&&next.equals("FAILED"))||(old.equals("FAILED")&&next.equals("SUCCEEDED"))){
   db.set(id+".review",true);db.set(event,next);if(fault.equals("before"))return "503 retry";db.commit();return "409 manual_review";
  }
  if(seq<=db.number(id+".seq"))return "200 stale";
  db.set(id+".status",next);db.set(id+".seq",seq);db.set(event,next);
  if(next.equals("SUCCEEDED"))db.set(id+".ledger",db.number(id+".ledger")+1);
  if(fault.equals("before"))return "503 retry";db.commit();
  return fault.equals("after")?"503 response_lost":"200 applied";
 }
}

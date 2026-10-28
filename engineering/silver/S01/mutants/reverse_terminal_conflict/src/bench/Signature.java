package bench;
import javax.crypto.Mac;import javax.crypto.spec.SecretKeySpec;import java.util.HexFormat;import java.nio.charset.StandardCharsets;import java.security.MessageDigest;
public final class Signature {
 public static boolean valid(String payload,String supplied)throws Exception{
  var mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec("fixture-only-not-production".getBytes(StandardCharsets.UTF_8),"HmacSHA256"));
  try{return MessageDigest.isEqual(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)),HexFormat.of().parseHex(supplied));}catch(IllegalArgumentException e){return false;}
 }
}

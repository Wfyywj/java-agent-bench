import java.util.Properties;
/** Local external-provider emulator. Deliberately non-idempotent issue;
controller must query first. */ final class QuotaProvider  {
    static boolean wasIssued(Properties ledger,String key)  {
        return ledger.containsKey("provider."+key);
    }
    static void issue(Properties ledger,String key)  {
        String k="provider."+key;
        int count=Integer.parseInt(ledger.getProperty(k,"0"));
        ledger.setProperty(k,Integer.toString(count+1));
    }
}

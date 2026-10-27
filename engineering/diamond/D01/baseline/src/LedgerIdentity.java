import java.util.Properties;
/** Identity is stable across legacy and sharded routes. */ final class LedgerIdentity  {
    static void validate(Properties state,String key,String amount)  {
        if(state.containsKey(key)&&!state.getProperty(key).equals(amount)) throw new IllegalArgumentException("identity-conflict");
    }
}

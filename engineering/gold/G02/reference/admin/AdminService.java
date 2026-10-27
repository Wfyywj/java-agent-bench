package admin;
import bills.Ledger;import billing.Engine;
/** Management facade deliberately cannot issue payment instructions. */
public final class AdminService {private final Ledger ledger;public AdminService(Ledger l){ledger=l;}public void publish(Engine.Rule r,String authenticatedRole){ledger.publish(r,authenticatedRole);}public Ledger.Diff preview(String id,String v,String actor,String reviewer){return ledger.rebuild(id,v,actor,reviewer);}}

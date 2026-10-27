package callers;
import sdk.AuthCache;import policy.Authority;
public final class Documents {private final AuthCache auth;public Documents(AuthCache a){auth=a;}public boolean read(String tenant,String subject,String doc,long now){return auth.allow(new Authority.Key(tenant,subject,doc,"read"),now);}public boolean edit(String tenant,String subject,String doc,long now){return auth.allow(new Authority.Key(tenant,subject,doc,"write"),now);}}

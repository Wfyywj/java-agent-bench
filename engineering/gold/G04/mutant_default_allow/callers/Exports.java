package callers;
import sdk.AuthCache;import policy.Authority;
public final class Exports {private final AuthCache auth;public Exports(AuthCache a){auth=a;}public boolean download(String tenant,String subject,String resource,long now){return auth.allow(new Authority.Key(tenant,subject,resource,"export"),now);}}

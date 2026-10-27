import java.io.IOException;

final class ReturnService {
    private final Store store;
    ReturnService(Store store) { this.store=store; }
    // The only writer serializes validation and snapshot publication together.
    synchronized Reply submit(ReturnRequest r, int fault) throws IOException {
        Loan l=store.loans.get(r.loan());
        if (l==null || !l.tenant().equals(r.tenant())) return new Reply(404,"NOT_FOUND");
        ReturnEvent previous=store.events.get(r.tenant()+"/"+r.token());
        if (!l.equipment().equals(r.equipment()) || !(l.state().equals("BORROWED") || l.state().equals("CLEANING"))) return new Reply(409,"NOT_RETURNABLE");
        Store next=new Store(store);
        String state=r.damaged()?"REVIEW":"CLEANING";
        String result="loan="+l.id()+";state="+state;
        next.loans.put(l.id(),new Loan(l.id(),l.tenant(),l.equipment(),state));
        fail(fault,1);
        next.events.put(r.tenant()+"/"+r.token(),new ReturnEvent(r.tenant(),r.loan(),r.token(),r.equipment(),r.damaged(),result));
        fail(fault,2);
        if (!r.damaged()) next.cleaning.add(l.id());
        fail(fault,3);
        store.commit(next);
        return new Reply(200,result);
    }
    private static void fail(int fault,int stage) throws IOException { if (fault==stage) throw new IOException("injected write failure"); }
}

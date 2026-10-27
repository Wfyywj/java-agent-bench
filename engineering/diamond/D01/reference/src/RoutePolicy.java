/** Route SDK boundary: old clients do not select storage themselves. */ final class RoutePolicy  {
    static String readStore(String phase)  {
        return phase.equals("NEW")?"new.":"old.";
    }
}

import com.sun.net.httpserver.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public final class App {
    public static void main(String[] args) throws Exception {
        ReturnService service=new ReturnService(new Store(Path.of(args[0]).toAbsolutePath()));
        HttpServer server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.setExecutor(Executors.newFixedThreadPool(4));
        server.createContext("/returns", exchange -> {
            Reply reply;
            try {
                if (!exchange.getRequestMethod().equals("POST")) reply=new Reply(405,"METHOD_NOT_ALLOWED");
                else {
                    byte[] body=exchange.getRequestBody().readNBytes(4097);
                    if(body.length>4096) throw new IllegalArgumentException();
                    Map<String,String> p=new HashMap<>();
                    for(String pair:new String(body,StandardCharsets.UTF_8).split("&")) {
                        String[] kv=pair.split("=",2);
                        if(kv.length!=2 || p.put(kv[0],URLDecoder.decode(kv[1],StandardCharsets.UTF_8))!=null) throw new IllegalArgumentException();
                    }
                    for(String field:List.of("tenant","loan","token","equipment"))
                        if(!p.getOrDefault(field,"").matches("[A-Za-z0-9_-]{1,64}")) throw new IllegalArgumentException();
                    if(!Set.of("true","false").contains(p.get("damaged"))) throw new IllegalArgumentException();
                    // Test-only fault injection: this app is a local development fixture, not production auth.
                    int fault=Integer.parseInt(exchange.getRequestHeaders().getFirst("X-Test-Fault")==null?"0":exchange.getRequestHeaders().getFirst("X-Test-Fault"));
                    reply=service.submit(new ReturnRequest(p.get("tenant"),p.get("loan"),p.get("token"),p.get("equipment"),Boolean.parseBoolean(p.get("damaged"))),fault);
                }
            } catch (IllegalArgumentException e) { reply=new Reply(400,"BAD_REQUEST"); }
              catch (Exception e) { reply=new Reply(503,"RETRY_LATER"); }
            byte[] out=reply.body().getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type","text/plain; charset=utf-8");
            exchange.sendResponseHeaders(reply.status(),out.length);
            try(var stream=exchange.getResponseBody()) { stream.write(out); }
        });
        server.start(); System.out.println(server.getAddress().getPort()); System.out.flush();
    }
}

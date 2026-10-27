import com.sun.net.httpserver.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.*;
public final class Server {
    public static void main(String[] args) throws Exception {
        var service = new PageService(new BoxRepository(Path.of(args[0])));
        var server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/boxes", exchange -> {
            int status = 200; String body;
            try {
                if (!exchange.getRequestMethod().equals("GET")) throw new IllegalArgumentException("invalid_method");
                Map<String,String> q = new HashMap<>();
                String raw = exchange.getRequestURI().getRawQuery();
                if (raw != null) for (String part : raw.split("&")) {
                    String[] kv = part.split("=",2);
                    q.put(URLDecoder.decode(kv[0], StandardCharsets.UTF_8), kv.length == 2 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "");
                }
                var page = service.query(q.getOrDefault("tenant",""), q.getOrDefault("status","all"),
                    q.getOrDefault("direction","asc"), Integer.parseInt(q.getOrDefault("limit","5")), q.getOrDefault("cursor",""));
                String items = String.join(",", page.items().stream().map(b -> "{\"id\":\""+b.id()+"\",\"receivedAt\":\""+b.receivedAt()+"\"}").toList());
                body = "{\"items\":["+items+"],\"next\":"+(page.next()==null ? "null" : "\""+page.next()+"\"")+"}";
            } catch (IllegalArgumentException e) { status=400; body="{\"error\":\"invalid_request\"}";
            } catch (Exception e) { status=500; body="{\"error\":\"internal_error\"}"; }
            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type","application/json");
            exchange.sendResponseHeaders(status, bytes.length);
            try (var out = exchange.getResponseBody()) { out.write(bytes); }
        });
        server.start(); System.out.println("PORT="+server.getAddress().getPort()); System.out.flush();
    }
}

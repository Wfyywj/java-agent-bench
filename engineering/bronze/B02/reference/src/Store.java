import java.nio.file.*;
import java.io.*;
import java.util.*;

/** Single-writer durable snapshot adapter, not a PostgreSQL transaction emulator. */
final class Store {
    final Path file;
    final Map<String, Loan> loans = new TreeMap<>();
    final Map<String, ReturnEvent> events = new TreeMap<>();
    final List<String> cleaning = new ArrayList<>();
    Store(Path file) throws IOException {
        this.file = file;
        for (String line : Files.readAllLines(file)) {
            String[] p = line.split("\t", -1);
            if (p[0].equals("L")) loans.put(p[1], new Loan(p[1],p[2],p[3],p[4]));
            if (p[0].equals("E")) events.put(p[1]+"/"+p[3],new ReturnEvent(p[1],p[2],p[3],p[4],Boolean.parseBoolean(p[5]),p[6]));
            if (p[0].equals("C")) cleaning.add(p[1]);
        }
    }
    Store(Store s) { file=s.file; loans.putAll(s.loans); events.putAll(s.events); cleaning.addAll(s.cleaning); }
    void commit(Store staged) throws IOException {
        List<String> rows = new ArrayList<>();
        staged.loans.values().forEach(l -> rows.add(String.join("\t","L",l.id(),l.tenant(),l.equipment(),l.state())));
        staged.events.values().forEach(e -> rows.add(String.join("\t","E",e.tenant(),e.loan(),e.token(),e.equipment(),""+e.damaged(),e.result())));
        staged.cleaning.forEach(c -> rows.add("C\t"+c));
        Path tmp=Files.createTempFile(file.getParent(),"snapshot-", ".tmp");
        try { Files.write(tmp,rows); Files.move(tmp,file,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING); }
        finally { Files.deleteIfExists(tmp); }
        loans.clear(); loans.putAll(staged.loans); events.clear(); events.putAll(staged.events);
        cleaning.clear(); cleaning.addAll(staged.cleaning);
    }
}

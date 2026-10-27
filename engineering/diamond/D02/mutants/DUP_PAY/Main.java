import java.nio.file.*;
import java.nio.channels.*;
import java.util.*;
import java.io.*;
public class Main extends BookingService  {
    public static void main(String[] a)throws Exception {
        dir=Path.of(a[0]);
        Files.createDirectories(dir);
        try(var lock=FileChannel.open(dir.resolve("lock"),StandardOpenOption.CREATE,StandardOpenOption.WRITE);var held=lock.lock()) {
            Path f=dir.resolve("state.properties");
            if(Files.exists(f))try(var in=Files.newInputStream(f)) {
                p.load(in);
            }
            try {
                run(Arrays.copyOfRange(a,1,a.length));
            }
            catch(IllegalArgumentException e) {
                System.out.println("REJECT "+e.getMessage());
                System.exit(2);
            }
        }
    }
}

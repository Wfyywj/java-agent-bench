import java.nio.file.*;
import java.io.*;
public final class Main {
 public static void main(String[] args) {
  if(args.length!=2) { System.err.println("usage: Main input.csv output.csv"); System.exit(64); }
  try { System.out.println(new Importer().run(Files.newInputStream(Path.of(args[0])),Path.of(args[1]).toAbsolutePath(),()->Thread.currentThread().isInterrupted())); }
  catch(IOException e) { System.out.println("IMPORT_IO line=0 imported=0"); System.exit(2); }
 }
}

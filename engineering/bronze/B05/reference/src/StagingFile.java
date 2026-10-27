import java.nio.file.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
/** A transaction-shaped file import: no partial publication on parse/cancel failure. */
final class StagingFile implements AutoCloseable {
 final Path temp, target; final BufferedWriter writer;
 StagingFile(Path target) throws IOException {
  this.target=target; temp=Files.createTempFile(target.getParent(), ".import-", ".tmp");
  try { writer=Files.newBufferedWriter(temp,StandardCharsets.UTF_8); }
  catch(IOException e) { Files.deleteIfExists(temp); throw e; }
 }
 void header() throws IOException { writer.write("label,name,email\n"); }
 void append(String id,String name,String email) throws IOException {
  writer.write(Csv.encode(id)+","+Csv.encode(name)+","+Csv.encode(email)); writer.newLine();
 }
 void commit() throws IOException { writer.close(); Files.move(temp,target,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING); }
 public void close() throws IOException { try { writer.close(); } finally { Files.deleteIfExists(temp); } }
}

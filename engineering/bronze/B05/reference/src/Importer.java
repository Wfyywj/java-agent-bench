import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.BooleanSupplier;
public final class Importer {
 public record Result(String code,int line,int imported) { public String toString(){return code+" line="+line+" imported="+imported;} }
 public Result run(InputStream input,Path target,BooleanSupplier cancelled) throws IOException {
  int line=0, count=0;
  try (BufferedReader reader=new BufferedReader(new InputStreamReader(input,StandardCharsets.UTF_8));
       StagingFile stage=new StagingFile(target)) {
   stage.header();
   String raw;
   Set<String> seen=new HashSet<>();
   while((raw=reader.readLine())!=null) {
    line++;
    if(cancelled.getAsBoolean()) return new Result("CANCELLED",line,0);
    if(line==1) { if(!raw.equals("label,name,email")) return new Result("CSV_HEADER",line,0); continue; }
    List<String> cells;
    try { cells=Csv.parse(raw); }
    catch(IllegalArgumentException e) { return new Result("CSV_SYNTAX",line,0); }
    if(cells.size()!=3 || !cells.get(0).matches("[A-Z][A-Z0-9-]{0,31}") || cells.get(1).isBlank() || !cells.get(2).contains("@"))
     return new Result("CSV_FIELDS",line,0);
    if(!seen.add(cells.get(0))) return new Result("CSV_DUPLICATE",line,0);
    stage.append(cells.get(0),cells.get(1),cells.get(2)); count++;
   }
   if(line==0) return new Result("CSV_HEADER",1,0);
   if(cancelled.getAsBoolean()) return new Result("CANCELLED",line,0);
   stage.commit(); return new Result("OK",line,count);
  }
 }
}

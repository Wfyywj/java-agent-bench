import java.util.*;
/** Nursery contract: one physical line per record, RFC-style quote escaping. */
final class Csv {
 static List<String> parse(String line) {
  List<String> cells=new ArrayList<>(); StringBuilder b=new StringBuilder();
  boolean quoted=false, ended=false;
  for(int i=0;i<line.length();i++) {
   char c=line.charAt(i);
   if(quoted) { if(c=='"') { if(i+1<line.length() && line.charAt(i+1)=='"') { b.append('"'); i++; } else {quoted=false; ended=true;} } else b.append(c); }
   else if(c==',') { cells.add(b.toString()); b.setLength(0); ended=false; }
   else if(c=='"' && b.length()==0 && !ended) quoted=true;
   else { if(ended || c=='"') throw new IllegalArgumentException(); b.append(c); }
  }
  if(quoted) throw new IllegalArgumentException(); cells.add(b.toString()); return cells;
 }
 static String encode(String value) { return "\""+value.replace("\"","\"\"")+"\""; }
}

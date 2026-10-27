import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.BooleanSupplier;
public class Verify {
 static int failures=0;
 static class Tracked extends ByteArrayInputStream {
  boolean closed=false;
  Tracked(String s){super(s.getBytes(StandardCharsets.UTF_8));}
  public void close() throws IOException {closed=true;super.close();}
 }
 static void check(String id,boolean ok){System.out.println((ok?"PASS ":"FAIL ")+id);if(!ok)failures++;}
 static boolean clean(Path d)throws Exception {try(var s=Files.list(d)){return s.noneMatch(x->x.getFileName().toString().startsWith(".import-"));}}
 // Independent output oracle: do not call candidate Csv.parse/encode.
 static List<String> outputCells(String row) {
  var pattern=java.util.regex.Pattern.compile("(?:\"((?:[^\"]|\"\")*)\"|([^\",]*))(,|$)");
  var cells=new ArrayList<String>(); int offset=0;
  while(true) {
   var match=pattern.matcher(row); match.region(offset,row.length());
   if(!match.lookingAt())throw new AssertionError("invalid committed CSV");
   cells.add(match.group(1)==null?match.group(2):match.group(1).replace("\"\"","\""));
   offset=match.end(); if(match.group(3).isEmpty())break;
  }
  return cells;
 }
 static void scenario(Path root,String id,String body,BooleanSupplier cancel,String code,int line,int count)throws Exception {
  Path d=Files.createDirectory(root.resolve(id)); Path out=d.resolve("labels.csv");Files.writeString(out,"previous\n");
  Tracked in=new Tracked(body);var result=new Importer().run(in,out,cancel);
  check(id+".result",result.code().equals(code)&&result.line()==line&&result.imported()==count);
  check(id+".ownership",in.closed&&clean(d));
  check(id+".atomic",code.equals("OK")?!Files.readString(out).equals("previous\n"):Files.readString(out).equals("previous\n"));
  check(id+".privacy",!result.toString().contains("private-person")&&!result.toString().contains("secret@example.test"));
 }
 public static void main(String[] a)throws Exception {
  Path root=Path.of(a[0]);String good="label,name,email\nN1,\"Fern, green\",secret@example.test\nN2,\"A \"\"quote\"\"\",a@b.test\n";
  scenario(root,"success",good,()->false,"OK",3,2);
  boolean contentOk=false;
  try {
   var output=Files.readAllLines(root.resolve("success/labels.csv"));
   contentOk=output.size()==3&&output.get(0).equals("label,name,email")
     &&outputCells(output.get(1)).equals(List.of("N1","Fern, green","secret@example.test"))
     &&outputCells(output.get(2)).equals(List.of("N2","A \"quote\"","a@b.test"));
  } catch(Exception|AssertionError malformedOutput) { contentOk=false; }
  check("success.output_header_and_escaped_fields",contentOk);
  scenario(root,"syntax","label,name,email\nN1,\"private-person,secret@example.test\n",()->false,"CSV_SYNTAX",2,0);
  scenario(root,"fields","label,name,email\nN1,private-person,secret@example.test,extra\n",()->false,"CSV_FIELDS",2,0);
  scenario(root,"duplicate","label,name,email\nN1,A,a@b\nN1,B,b@c\n",()->false,"CSV_DUPLICATE",3,0);
  scenario(root,"cancel",good,()->true,"CANCELLED",1,0);
  scenario(root,"empty","",()->false,"CSV_HEADER",1,0);
  Path d=Files.createDirectory(root.resolve("repeat"));boolean closed=true;
  for(int i=0;i<120;i++){Tracked in=new Tracked(i%2==0?good:"label,name,email\nmalformed\n");new Importer().run(in,d.resolve("labels.csv"),()->false);closed &= in.closed;}
  check("B05-A04.repeat120.zero-tolerance",closed&&clean(d));
  // Exception before staging creation must still release transferred input ownership.
  Tracked in=new Tracked(good);boolean failed=false;
  try{new Importer().run(in,root.resolve("missing/labels.csv"),()->false);}catch(IOException expected){failed=true;}
  check("B05-A02.setup-failure",failed&&in.closed);
  // Genuine underlying read failure, independent from CSV parser's controlled errors.
  InputStream broken=new InputStream(){boolean closed; public int read()throws IOException{throw new IOException("synthetic read fault");} public void close(){closed=true;}};
  // A separate close counter avoids relying on implementation introspection.
  final boolean[] ended={false};
  InputStream fault=new FilterInputStream(broken){public void close()throws IOException{ended[0]=true;super.close();}};
  try{new Importer().run(fault,d.resolve("labels.csv"),()->false);}catch(IOException expected){}
  check("B05-A02.read-failure",ended[0]&&clean(d));
  if(failures>0)System.exit(1);
 }
}

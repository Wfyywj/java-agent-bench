import java.nio.file.*;
import java.nio.channels.*;
import java.util.*;
import java.io.*;
/** Domain orchestration boundary; persistence and CLI are separate modules. */
class PluginPolicyRuntime extends DurableState {
    static final String FAULT="UNLOCKED";
    static void run(String[] a)throws Exception {
        String op=a[0];
        switch(op) {
            case "review"-> {
                Properties manifest=new Properties();
                try(var in=Files.newInputStream(Path.of(a[1]))) {
                    manifest.load(in);
                }
                String dep=manifest.getProperty("dependency",""),perm=manifest.getProperty("permissions","");
                require(FAULT.equals("UNLOCKED")||dep.equals("builtin-expression@1#original-2026"),"dependency-lock");
                require(FAULT.equals("PERMISSION")||perm.equals("compute"),"forbidden-permission");
                require(manifest.getProperty("format","").equals("expression-v1"),"legacy-migration-required");
                set("approved."+a[2],true);
                audit("review "+a[2]+" locked="+dep+" permissions="+perm);
            }
            case "execute"-> {
                require(get("approved."+a[1],"false").equals("true"),"unapproved");
                int steps=Integer.parseInt(a[2]);
                require(FAULT.equals("UNBOUNDED")||(steps>=0&&steps<=1000),"cpu-budget");
                require(a[3].length()<=128,"memory-input-bound");
                require(a[3].matches("[0-9+ ]+"),"no-code-or-network");
                long total=0;
                for(String s:a[3].split("\\+"))total=Math.addExact(total,Long.parseLong(s.trim()));
                set("result."+a[1],total);
                audit("execute "+a[1]+" redacted-input steps="+steps);
                System.out.println(total);
            }
            case "marker"-> {
                require(FAULT.equals("PERMISSION"),"host-write-forbidden");
                Files.writeString(dir.resolve("harmless-marker"),"boundary failure");
            }
            default->throw new IllegalArgumentException("command");
        }
        save();
    }
}

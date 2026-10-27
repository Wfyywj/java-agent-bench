package workorders;
import upload.Sessions;import java.nio.file.Path;import java.util.*;
public final class Attachments {private final Sessions uploads;private final Map<String,Set<Path>> work=new HashMap<>();public Attachments(Sessions s){uploads=s;}public void attach(String workId,String session){Path p=uploads.link(session);work.computeIfAbsent(workId,k->new HashSet<>()).add(p);}public int count(String workId){return work.getOrDefault(workId,Set.of()).size();}}

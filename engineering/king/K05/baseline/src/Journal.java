import java.nio.channels.*;
import java.nio.file.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.CRC32;
/** Single-host durable command log. File lock serializes fencing check and append. */
final class Journal implements AutoCloseable  {
    private final FileChannel channel;
    private final FileLock lock;
    Journal(Path path) throws Exception  {
        channel=FileChannel.open(path,StandardOpenOption.CREATE,StandardOpenOption.READ,StandardOpenOption.WRITE);
        lock=channel.lock();
    }
    List<String> read() throws Exception  {
        long length=channel.size();
        if(length>1048576) throw new IllegalStateException("journal-limit");
        ByteBuffer b=ByteBuffer.allocate((int)length);
        channel.position(0);
        while(b.hasRemaining()) if(channel.read(b)<0) break;
        String data=new String(b.array(),StandardCharsets.UTF_8);
        if(!data.isEmpty()&&!data.endsWith("\n")) throw new IllegalStateException("torn-journal");
        List<String> commands=new ArrayList<>();
        for(String line:data.split("\n"))  {
            if(line.isEmpty())continue;
            int i=line.lastIndexOf('|');
            if(i<0)throw new IllegalStateException("corrupt-journal");
            String cmd=line.substring(0,i);
            if(!checksum(cmd).equals(line.substring(i+1)))throw new IllegalStateException("corrupt-journal");
            commands.add(cmd);
        }
        return commands;
    }
    static String checksum(String s)  {
        CRC32 crc=new CRC32();
        crc.update(s.getBytes(StandardCharsets.UTF_8));
        return Long.toHexString(crc.getValue());
    }
    void append(String command) throws Exception  {
        byte[] bytes=(command+"|"+checksum(command)+"\n").getBytes(StandardCharsets.UTF_8);
        channel.position(channel.size());
        ByteBuffer b=ByteBuffer.wrap(bytes);
        while(b.hasRemaining())channel.write(b);
        channel.force(true);
    }
    public void close() throws Exception  {
        lock.release();
        channel.close();
    }
}

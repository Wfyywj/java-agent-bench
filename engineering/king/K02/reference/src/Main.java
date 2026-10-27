import java.nio.file.*;
public final class Main  {
    public static void main(String[] args)  {
        try  {
            if(args.length<2)throw new IllegalArgumentException("arguments");
            String command=args[1];
            Protocol.parse(command);
            try(Journal journal=new Journal(Path.of(args[0])))  {
                Domain domain=new Domain();
                for(String old:journal.read())domain.apply(Protocol.parse(old));
                String result=domain.apply(Protocol.parse(command));
                if(args.length>2&&args[2].equals("before")) {
                    System.out.println("UNKNOWN before");
                    return;
                }
                journal.append(command);
                if(args.length>2&&args[2].equals("after")) {
                    System.out.println("UNKNOWN after");
                    return;
                }
                System.out.println(result);
            }
        }
        catch(Exception e)  {
            System.out.println("REJECT "+e.getMessage());
        }
    }
}

/** Public wire grammar, shared by live requests and journal replay. */
final class Protocol  {
    static String[] parse(String command)  {
        if(!command.matches("[A-Za-z0-9_ .:-]{1,512}")) throw new IllegalArgumentException("encoding");
        return command.split(" +");
    }
}

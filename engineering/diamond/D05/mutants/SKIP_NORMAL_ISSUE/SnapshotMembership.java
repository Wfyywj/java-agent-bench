/** Frozen member list;
restoring a job never reads a live paginated list. */ final class SnapshotMembership  {
    static String at(String frozen,int index)  {
        String[] members=frozen.split(",");
        if(index<0||index>=members.length) throw new IllegalArgumentException("done");
        return members[index];
    }
}

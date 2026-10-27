record Loan(String id, String tenant, String equipment, String state) {}
record ReturnRequest(String tenant, String loan, String token, String equipment, boolean damaged) {}
record ReturnEvent(String tenant, String loan, String token, String equipment, boolean damaged, String result) {}
record Reply(int status, String body) {}

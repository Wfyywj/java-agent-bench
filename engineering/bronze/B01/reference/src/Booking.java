import java.time.*;
public record Booking(String site,String slot,String building,Instant start,Instant end,String status,String note) {}

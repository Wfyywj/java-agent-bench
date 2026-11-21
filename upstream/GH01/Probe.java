import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;

import java.io.StringReader;

public class Probe {
    private static String readNumberText(String literal) throws Exception {
        try (JsonReader reader = new JsonReader(new StringReader("[" + literal + "]"))) {
            reader.setLenient(false);
            reader.beginArray();
            expect(JsonToken.NUMBER, reader.peek(), "peek for " + literal);
            String text = reader.nextString();
            reader.endArray();
            expect(JsonToken.END_DOCUMENT, reader.peek(), "end of document for " + literal);
            return text;
        }
    }

    private static void expect(Object expected, Object actual, String operation) {
        if (!expected.equals(actual)) {
            throw new AssertionError(operation + " expected <" + expected + "> but got <" + actual + ">");
        }
    }

    private static void checkNumericReads() throws Exception {
        try (JsonReader reader = new JsonReader(new StringReader("[-0, -0, 3]"))) {
            reader.setLenient(false);
            reader.beginArray();
            expect(Double.doubleToRawLongBits(-0.0d), Double.doubleToRawLongBits(reader.nextDouble()),
                    "nextDouble sign bit for -0");
            expect(0L, reader.nextLong(), "nextLong for -0");
            expect(3, reader.nextInt(), "element following -0");
            reader.endArray();
            expect(JsonToken.END_DOCUMENT, reader.peek(), "end of mixed array");
        }
    }

    public static void main(String[] args) {
        String[] numbers = {
                "-0", "0", "17", "-17", "-0.0", "-0e0",
                "9223372036854775807", "-9223372036854775808", "9223372036854775808"
        };
        int failures = 0;
        for (String number : numbers) {
            try {
                expect(number, readNumberText(number), "nextString for " + number);
                System.out.println("PASS number text for " + number);
            } catch (AssertionError | Exception e) {
                System.out.println("FAIL " + e);
                failures++;
            }
        }
        try {
            checkNumericReads();
            System.out.println("PASS signed double, integer zero and following element");
        } catch (AssertionError | Exception e) {
            System.out.println("FAIL " + e);
            failures++;
        }
        if (failures > 0) {
            System.exit(1);
        }
    }
}

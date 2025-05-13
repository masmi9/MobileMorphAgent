package payloads_source;

public class Payload {
    public void execute() {
        try {
            // Replace this with any code you want executed
            Process process = Runtime.getRuntime().exec("ls /data/data");
            java.io.BufferedReader reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(process.getInputStream())
            );
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("[Payload] " + line);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
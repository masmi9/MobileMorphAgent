package src.main.java.com.agent.util;
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class ShellExecutor {
    public static String execute(String cmd) {
        try {
            Process process = Runtime.getRuntime().exec(cmd);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            StringBuilder output = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) output.append(line).append("\n");
            return output.toString();
        } catch (Exception e) {
            return e.toString();
        }
    }
}
package com.mobilemorph.agent.utils;
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class ShellExecutor {
    public static String execute(String cmd) {
        StringBuilder output = new StringBuilder();
        try {
            Process process = Runtime.getRuntime().exec(cmd);
            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = reader.readLine()) != null) {
                output.append(line).append("\n");
            }
            process.waitFor();
        } catch (Exception e) {
            output.append("Error: ").append(e.getMessage());
        }
        return output.toString();
    }
}
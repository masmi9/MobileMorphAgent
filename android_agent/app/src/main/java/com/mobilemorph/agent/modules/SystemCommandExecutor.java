package com.mobilemorph.agent.modules;

import android.util.Log;

import com.mobilemorph.agent.utils.ShellExecutor;

import org.json.JSONObject;

/**
 * SystemCommandExecutor - Executes shell commands on the device.
 *
 * Wraps the existing ShellExecutor utility as a proper agent module
 * with JSON-based input/output, making it available through the
 * MobileMorphAgentBridge for DYNA integration.
 *
 * Similar to: drozer run shell.exec / run system.exec
 */
public class SystemCommandExecutor {
    private static final String TAG = "SystemCommandExecutor";

    public JSONObject execute(JSONObject args) {
        try {
            String command = args.getString("command");
            Log.i(TAG, "Executing shell command: " + command);

            String output = ShellExecutor.execute(command);

            JSONObject data = new JSONObject();
            data.put("command", command);
            data.put("output", output);

            return createResponse("success", data, null);

        } catch (Exception e) {
            Log.e(TAG, "Command execution failed", e);
            return createResponse("error", null, "Execution failed: " + e.getMessage());
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

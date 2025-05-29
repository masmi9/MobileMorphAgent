package com.mobilemorph.agent.utils;

import android.content.Context;
import android.util.Log;

import androidx.security.crypto.EncryptedFile;
import androidx.security.crypto.MasterKeys;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.lang.reflect.Method;

import dalvik.system.DexClassLoader;

public class EncryptedDexLoader {

    public static void decryptAndLoadDex(Context context, String encryptedFileName, String optimizedDirName, String classNameToInvoke, String methodName) {
        try {
            String masterKeyAlias = MasterKeys.getOrCreate(MasterKeys.AES256_GCM_SPEC);
            File encryptedDexFile = new File(context.getFilesDir(), encryptedFileName);

            EncryptedFile encryptedFile = new EncryptedFile.Builder(
                    encryptedDexFile,
                    context,
                    masterKeyAlias,
                    EncryptedFile.FileEncryptionScheme.AES256_GCM_HKDF_4KB
            ).build();

            InputStream in = encryptedFile.openFileInput();
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] data = new byte[1024];
            int nRead;
            while ((nRead = in.read(data, 0, data.length)) != -1) {
                buffer.write(data, 0, nRead);
            }
            buffer.flush();

            File decryptedDex = new File(context.getCacheDir(), "decrypted.dex");
            java.nio.file.Files.write(decryptedDex.toPath(), buffer.toByteArray());

            File optimizedDir = new File(context.getCodeCacheDir(), optimizedDirName);
            if (!optimizedDir.exists()) optimizedDir.mkdirs();

            DexClassLoader dexClassLoader = new DexClassLoader(
                    decryptedDex.getAbsolutePath(),
                    optimizedDir.getAbsolutePath(),
                    null,
                    context.getClassLoader()
            );

            Class<?> loadedClass = dexClassLoader.loadClass(classNameToInvoke);
            Method method = loadedClass.getDeclaredMethod(methodName, Context.class);
            method.setAccessible(true);
            method.invoke(null, context);

        } catch (Exception e) {
            Log.e("EncryptedDexLoader", "Failed to decrypt and load dex", e);
        }
    }
}

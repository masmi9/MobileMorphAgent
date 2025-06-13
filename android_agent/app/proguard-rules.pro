# --- OkHttp / TLS platform reflection --------------------------------
# OkHttp checks whether these providers exist at runtime; they can be absent.
-dontwarn org.bouncycastle.**
-dontwarn org.conscrypt.**
-dontwarn org.openjsse.**

# Keep the tiny “Platform” shim classes inside OkHttp so reflection works
-keep class okhttp3.internal.platform.** { *; }

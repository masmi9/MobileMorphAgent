#!/bin/bash

# === CONFIG ===
REPO_ROOT="$(pwd)"
APK_DIR="$REPO_ROOT/app/build/outputs"
APK_NAME="mmagent.apk"
APK_OUTPUT="$APK_DIR/apk/debug/$APK_NAME"
KEYSTORE_PATH="./debug.keystore"
KEY_ALIAS="androiddebugkey"
KEYSTORE_PASS="android"
KEY_PASS="android"
PACKAGE_NAME="com.mobilemorph.agent"
BUNDLETOOL_JAR="tools/bundletool-all-1.18.1.jar"

echo "[+] Cleaning previous builds..."
./gradlew clean

echo "[+] Assembling debug APK..."
./gradlew assembleDebug

# Ensure APK was built
if [ ! -f "$APK_OUTPUT" ]; then
    echo "[!] Build failed: APK not found at $APK_OUTPUT"
    exit 1
fi

# Generate debug keystore if not exists
if [ ! -f "$KEYSTORE_PATH" ]; then
    echo "[+] Generating debug keystore..."
    keytool -genkeypair -v -keystore "$KEYSTORE_PATH" -storepass "$KEYSTORE_PASS" \
        -alias "$KEY_ALIAS" -keypass "$KEY_PASS" -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Android Debug,O=Android,C=US"
fi

echo "[+] Signing APK with v1, v2, and v3 signature schemes..."
apksigner sign \
  --ks "$KEYSTORE_PATH" \
  --ks-key-alias "$KEY_ALIAS" \
  --ks-pass pass:"$KEYSTORE_PASS" \
  --key-pass pass:"$KEY_PASS" \
  --v1-signing-enabled true \
  --v2-signing-enabled true \
  --v3-signing-enabled true \
  --out "$APK_OUTPUT" \
  "$APK_OUTPUT"

echo "[+] Verifying APK signature..."
apksigner verify --verbose --print-certs "$APK_OUTPUT"
if [ $? -ne 0 ]; then
    echo "[!] APK signing verification failed."
    exit 1
fi

echo "[+] Installing $APK_NAME on device..."
adb install -r "$APK_OUTPUT"
if [ $? -eq 0 ]; then
    echo "[✓] Installed $APK_NAME successfully!"
else
    echo "[!] Failed to install APK."
    exit 1
fi

# Optional: Force start the agent manually
# echo "[+] Starting CommandService..."
# adb shell am startservice $PACKAGE_NAME/.services.CommandService

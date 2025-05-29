#!/bin/bash

# === CONFIG ===
REPO_ROOT="$(pwd)"
APK_DIR="$REPO_ROOT/app/build/outputs"
SIGNED_APK_NAME="mmagent.apk"
SIGNED_APK_PATH="$APK_DIR/apk/debug/$SIGNED_APK_NAME"
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

# Find actual debug APK
ACTUAL_APK=$(find "$APK_DIR/apk/debug" -name "*-debug.apk" | sort -r | head -n 1)

if [ ! -f "$ACTUAL_APK" ]; then
    echo "[!] Build failed: Could not find any debug APK in $APK_DIR/apk/debug"
    exit 1
fi

echo "[✓] Found debug APK: $ACTUAL_APK"
echo "[+] Copying and renaming to $SIGNED_APK_PATH"
cp "$ACTUAL_APK" "$SIGNED_APK_PATH"

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
  --out "$SIGNED_APK_PATH" \
  "$SIGNED_APK_PATH"

echo "[+] Verifying APK signature..."
apksigner verify --verbose --print-certs "$SIGNED_APK_PATH"
if [ $? -ne 0 ]; then
    echo "[!] APK signing verification failed."
    exit 1
fi

echo "[+] Installing $SIGNED_APK_NAME on device..."
adb install -r "$SIGNED_APK_PATH"
if [ $? -eq 0 ]; then
    echo "[✓] Installed $SIGNED_APK_NAME successfully!"
else
    echo "[!] Failed to install APK."
    exit 1
fi

# Optional: Start agent service (uncomment if needed)
# echo "[+] Starting CommandService..."
# adb shell am startservice $PACKAGE_NAME/.services.CommandService

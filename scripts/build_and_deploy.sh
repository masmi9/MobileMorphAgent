#!/bin/bash

# === CONFIG ===
APK_DIR="../android_agent/app/build/outputs/apk/debug"
APK_NAME="mmagent.apk"
APK_INPUT="$APK_DIR/app-debug.apk"
APK_OUTPUT="$APK_DIR/$APK_NAME"
PACKAGE_NAME="com.mobilemorph.agent"

cd ./android_agent || exit 1

echo "[+] Cleaning previous builds..."
./gradlew clean

echo "[+] Assembling debug APK..."
./gradlew assembleDebug

# Ensure APK was built
if [ ! -f "$APK_INPUT" ]; then
    echo "[!] Build failed: APK not found at $APK_INPUT."
    exit 1
fi

echo "[+] Renaming APK to $APK_NAME..."
mv "$APK_INPUT" "$APK_OUTPUT"

echo "[+] Installing $APK_NAME to device..."
adb install -r "$APK_OUTPUT"

if [ $? -eq 0 ]; then
    echo "[✓] Installed $APK_NAME successfully!"
else
    echo "[!] Failed to install APK."
    exit 1
fi

# Optional: Force start the agent manually (if needed)
# echo "[+] Starting CommandService..."
# adb shell am startservice $PACKAGE_NAME/.services.CommandService

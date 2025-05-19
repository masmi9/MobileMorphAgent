#!/bin/bash

# === CONFIG ===
JAVA_SRC="payloads_source/com/payload/Payload_AppScanner.java"
CLASS_DIR="out"
DEX_OUT="payloads_dex"
DEX_FILE="payloads/app_scanner.dex"
ANDROID_JAR="$ANDROID_HOME/platforms/android-33/android.jar"

# === CHECKS ===
if [ ! -f "$JAVA_SRC" ]; then
    echo "[!] Source file not found: $JAVA_SRC"
    exit 1
fi

if [ ! -f "$ANDROID_JAR" ]; then
    echo "[!] Android jar not found at: $ANDROID_JAR"
    echo "    Please check your \$ANDROID_HOME"
    exit 1
fi

# === CLEAN & COMPILE ===
echo "[+] Compiling $JAVA_SRC..."
rm -rf $CLASS_DIR $DEX_OUT $DEX_FILE
mkdir -p $CLASS_DIR $DEX_OUT payloads

javac -classpath "$ANDROID_JAR" -d $CLASS_DIR "$JAVA_SRC"
if [ $? -ne 0 ]; then
    echo "[!] Java compilation failed"
    exit 1
fi

# === DEX CONVERSION ===
echo "[+] Converting to DEX..."
d8 --output=$DEX_OUT $CLASS_DIR
if [ $? -ne 0 ]; then
    echo "[!] DEX conversion failed"
    exit 1
fi

mv $DEX_OUT/classes.dex "$DEX_FILE"

# === DEPLOY TO DEVICE ===
echo "[+] Pushing to device..."
adb push "$DEX_FILE" /sdcard/MobileMorphAgent/payloads/

echo "[✓] Payload built and pushed: $DEX_FILE"

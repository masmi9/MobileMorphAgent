#!/usr/bin/env bash
set -euo pipefail

### === CONFIG ===
REPO_ROOT="$(pwd)"
APK_DIR="$REPO_ROOT/app/build/outputs/apk/release"
AAB_DIR="$REPO_ROOT/app/build/outputs/bundle/release"
KEYSTORE_PATH="$REPO_ROOT/keystore/mmagent.jks"
KEY_ALIAS="mmagent"
PACKAGE_NAME="com.mobilemorph.agent"
BUNDLETOOL_JAR="$REPO_ROOT/tools/bundletool-all-1.18.1.jar"   # optional

### === ENV PASSES ===
KS_PASS="${KEYSTORE_PASS:?Set KEYSTORE_PASS in your shell}"
KP_PASS="${KEY_PASS:?Set KEY_PASS in your shell}"

### === 1. CLEAN ===
echo "[+] Cleaning previous builds…"
./gradlew clean

### === 2. BUILD SIGNED RELEASE APK ===
echo "[+] Assembling signed *release* APK (v2/v3/v4)…"
./gradlew assembleRelease            # or: ./gradlew bundleRelease for an .aab

### === 3. LOCATE THE APK ===
RELEASE_APK=$(find "$APK_DIR" -name '*-release.apk' | sort -r | head -n 1)
if [[ ! -f "$RELEASE_APK" ]]; then
  echo "[!] Build failed: no release APK found in $APK_DIR"
  exit 1
fi
echo "[✓] Found release APK: $RELEASE_APK"

### === 4. VERIFY ALL SIGNATURES, INCLUDING v4 ===
IDSIG_FILE="${RELEASE_APK}.idsig"   # Gradle creates this when v4SigningEnabled = true
echo "[+] Verifying v2/v3/v4 signatures…"
apksigner verify --verbose --print-certs \
  --v4-signature-file "$IDSIG_FILE" \
  "$RELEASE_APK"

### === 5. (OPTIONAL) BUILD A UNIVERSAL .APKS FROM THE .AAB ===
# If you prefer installing the AAB-based universal APK set instead of the plain APK:
# AAB=$(find "$AAB_DIR" -name '*.aab' | sort -r | head -n 1)
# if [[ -f "$AAB" ]]; then
#   echo "[+] Converting AAB → universal .apks for local install…"
#   java -jar "$BUNDLETOOL_JAR" build-apks \
#        --bundle "$AAB" \
#        --output mmagent.apks \
#        --ks "$KEYSTORE_PATH" --ks-pass pass:"$KS_PASS" \
#        --ks-key-alias "$KEY_ALIAS" --key-pass pass:"$KP_PASS" \
#        --mode=universal
#   RELEASE_APK="mmagent.apks"
# fi

### === 6. INSTALL ON CONNECTED DEVICE ===
echo "[+] Installing on device…"
adb install -r "$RELEASE_APK"
echo "[✓] Install complete."

### === 7. (OPTIONAL) START THE COMMAND SERVICE ===
# echo "[+] Starting CommandService…"
# adb shell am startservice "$PACKAGE_NAME"/.services.CommandService

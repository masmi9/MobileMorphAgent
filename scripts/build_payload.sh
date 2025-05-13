#!/bin/bash
set -e

mkdir -p out

echo "[*] Compiling Payload.java..."
javac -d out payloads_source/Payload.java

echo "[*] Converting to DEX..."
# Make sure d8 is in your PATH or provide the full path
d8 --output=payloads_dex out

echo "[*] Moving and renaming..."
mkdir -p payloads
mv payloads_dex/classes.dex payloads/test_payload.dex

echo "[+] Built test_payload.dex at payloads/test_payload.dex"

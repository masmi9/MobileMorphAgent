# MobileMorphAgent Enhancement Roadmap

This roadmap outlines how to elevate MobileMorphAgent beyond the capabilities of Drozer. It includes architectural improvements, new exploit modules, better C2 management, and usability upgrades.

---

## 🎯 Core Features

### ✅ Agent Improvements

* [] Implement stealth techniques (e.g., job-scheduling, encryption at rest)
* [✓] Use WorkManager or JobScheduler instead of `startService` to avoid foreground alerts
* [✓] Persist agent after reboot using `BOOT_COMPLETED` + `ForegroundService`
* [✓] Hide launcher icon programmatically post-install
* [✓] Encrypted local storage for payloads/configs

### ✅ Command and Control (C2)

* [✓] Migrate to WebSocket for real-time command delivery (instead of polling)
* [✓] Use HTTPS with self-signed or Let’s Encrypt certs
* [✓] Integrate API token authentication with rotation capability
* [✓] Provide session view in dashboard: list of active devices, timestamps, OS info
* [ ] Implement upload/download file endpoints via base64 or multipart

---

## 💉 Exploitation Modules

### ✅ Content Provider Exploits

* [ ] Automate discovery of exported providers with no permissions
* [ ] Add read/write/delete PoCs with proof-of-concept log output

### ✅ WebView & JSInterface

* [ ] Enumerate WebViews and exposed JS interfaces
* [ ] Attempt remote code execution via `evaluateJavascript()` where applicable

### ✅ IPC Abuse

* [ ] Scan for exported services, receivers, and activities with no permission check
* [ ] Add Intent Fuzzer module (like Drozer’s `scanner.fuzzing.intent`) to test intent injections

### ✅ App Misconfigurations

* [ ] Add analyzer for `android:sharedUserId`, `taskAffinity`, `allowBackup`, and debuggable
* [ ] Combine this with a MASVS static checklist

---

## 🧠 Intelligence & Persistence

### ✅ Dynamic Reflection

* [ ] Implement dynamic analysis hooks for Java Reflection and ClassLoader abuse
* [ ] Alert on usage of `loadClass`, `newInstance`, `DexClassLoader` from suspicious paths

### ✅ Frida Automation

* [ ] Expose optional endpoint to send `.js` scripts to `frida-server` runtime
* [ ] Create a Frida hook manager module

---

## 🌐 Dashboard (C2 UI)

### ✅ Live Device Panel

* [✓] Show real-time connected agents with device ID, manufacturer, root status
* [✓] Enable manual command injection and output collection per device

### ✅ Modules Panel

* [ ] List available modules (e.g., URI traversal, shell exec, file upload)
* [ ] Send modules as on-demand payloads

### ✅ Payload Manager

* [ ] Allow uploading `.dex` payloads from UI
* [ ] Option to deploy and execute payload immediately or queue for later

---

## 🚀 Operational Enhancements

### ✅ CI/CD

* [ ] Add GitHub Actions or GitLab CI pipeline to auto-build and sign agent
* [ ] Add self-updating APK delivery mechanism (polls server for updated .apk or .dex)

### ✅ Play Store Readiness (for PoC only)

* [ ] Add release signing support with Play App Signing compatibility
* [ ] Implement ProGuard / R8 obfuscation with shrinking rules
* [ ] Use productFlavors for `debug`, `research`, and `stealth` builds

---

## 📎 Notes

* All sensitive actions should be protected by shared HMAC or bearer token auth
* All payloads should be assumed malicious or suspicious by nature
* Limit agent behavior to research or pentesting on authorized devices only

---

Would you like to divide this roadmap into versioned milestones or weekly sprint objectives?



Top 5 Next Priorities
1. ✅ Add Execution Support for Exploit Modules (High Priority)
Implement modular C2 dispatch for:

uri_traversal (already stubbed in main.py)

Future modules like intent_injection, sql_injection, jsinterface_enum

Action:

Build a modules/ directory with reusable exploit templates.

Add UI buttons to trigger them from the dashboard.

Route responses to the command_result socket handler.


2. 🧪 Implement Dynamic Reflection Detection
Add Frida hooks or Java method logging to flag:

DexClassLoader, loadClass, Class.forName, invoke

Action:

Integrate with a future Frida hook module.

Add /frida_hook route to push .js scripts to devices.

3. 🧠 Add Static Misconfiguration Parser (MASVS Enhancer)
You started parsing AndroidManifest.xml—extend this.

Action:

Add checks for:

android:sharedUserId

allowBackup="true"

taskAffinity != default

Missing android:permission on exported components

4. 🔃 Self-Updating APK or Dex Mechanism
Add an endpoint in main.py:

/check_update → tells agent if new .apk or .dex is available

Agent can:

Download & install the new APK silently (rooted)

Or pull updated .dex for hotpatching via DexLoader
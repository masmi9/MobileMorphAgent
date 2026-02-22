MobileMorphAgent is a modular Android Command & Control (C2) research
  framework designed to replace and improve upon Drozer. It's built for
  authorized Android security testing, red team operations, and mobile
  malware research.

  Core Architecture

  The project uses a dual-connectivity C2 architecture:

  Desktop Client/Dashboard
      ↓
  Flask C2 Server (Python + SocketIO)
      ↓
  Android Agent (APK)
      ├─ WebSocket Mode (CommandService) - Remote real-time C2
      └─ TCP Socket Mode (ServerSocketService) - Local ADB port forwarding
  (Drozer replacement)

  Tech Stack

  - Backend: Python, Flask, Flask-SocketIO, Eventlet
  - Android: Java 17, Kotlin, Gradle (API 26+, targeting 33)
  - Libraries: OkHttp 5.1.0, Gson, Socket.IO client, AndroidX Security
  - Native: C/C++ ptrace injector
  - Analysis: Frida, CodeQL (automated security scanning)

  Key Capabilities

  1. Android Agent Features

  - Remote shell command execution
  - Dynamic .dex payload injection (AES256-GCM encrypted)
  - Native binary injection via ptrace (x86_64/ARM64)
  - Frida runtime hooking
  - Boot persistence with BOOT_COMPLETED receiver
  - Stealth mode (hides launcher icon)
  - Runs as foreground service for reliability

  2. Seven Built-in Exploitation Modules

  1. PackageEnumerator - Lists apps, shows exported components
  2. ManifestAnalyzer - Scans for misconfigurations
  3. PermissionAuditor - Maps permissions to capabilities
  4. IntentExploiter - Fuzzes intent-based vulnerabilities
  5. ContentProviderExploiter - Tests exposed providers
  6. WebViewExploiter - Finds JSInterface exploits
  7. IPCExploiter - Tests IPC abuse vectors

  3. C2 Server Features

  - REST API with token authentication
  - WebSocket real-time communication
  - Web dashboard at localhost:5000
  - Agent status monitoring
  - Command queueing and result retrieval
  - Telemetry export (JSON)

  Recent Development (Last 5 Commits)

  The most recent work focused on:

  1. Drozer Replacement Architecture (commit 18e270b)
    - Added ServerSocketService for ADB port forwarding
    - Enables local desktop client control via adb forward tcp:31415
  tcp:31415
    - Implements Drozer-like command protocol
  2. WebSocket Connection Fixes (commit 9682918)
    - Fixed critical bugs in CommandService.java
    - Restored JSON parsing and command execution
    - Added comprehensive documentation
  3. CodeQL Integration (commit f9f6a31)
    - Automated security analysis for Java, Python, C/C++, JavaScript
  4. Dependency Updates
    - OkHttp 4.9.3 → 5.1.0
    - Kotlin stdlib updates
    - GitHub Actions runner upgrades

  Project Structure

  android_agent/           - Main Android APK source
  ├── services/           - CommandService, ServerSocketService
  ├── modules/            - 7 exploitation modules
  ├── utils/              - DexLoader, ShellExecutor, etc.
  └── frida/              - Frida hook manager

  morph_server/server/    - Flask C2 backend
  core/                   - Drozer replacement helpers
  frida_hooks/            - Pre-built Frida scripts
  injector/               - Native ptrace injector (C)
  payloads_source/        - DEX payload source code

  Documentation

  - README.md - Project overview, features, legal disclaimer
  - AGENT_SERVER_CONNECTION_GUIDE.md - Connection flows, troubleshooting
  - ROADMAP.md - Future development plans
  - QUICK_TEST.md - Setup and testing guide

  Current State

  The project is actively maintained and functional with:
  - [Done] Working WebSocket C2 connection
  - [Done] Working ADB port forwarding mode (Drozer replacement)
  - [Done] All 7 exploitation modules operational
  - [Done] DEX and native injection working
  - [Done] CI/CD with CodeQL security scanning
  - [Done] Comprehensive test scripts (test_connection.py)
  - [In Progress] Development build configuration (cleartext HTTP enabled)
  - [To Do] ROADMAP items pending (stealth improvements, Play Store readiness)

  Key Files to Explore

  - morph_server/server/main.py:1 - C2 server entry point
  - android_agent/app/src/main/java/com/mobilemorph/agent/services/CommandS
  ervice.java:1 - WebSocket agent
  - android_agent/app/src/main/java/com/mobilemorph/agent/services/ServerSo
  cketService.java:1 - ADB socket agent
  - agent_client.py:1 - Desktop client for ADB mode
  - dyna.py:1 - OWASP MASTG integration
  - injector/injector.c:1 - Native ptrace injector

  Bottom Line: This is a sophisticated, well-architected Android security
  testing framework with dual C2 modes, comprehensive exploitation
  capabilities, and active development focused on replacing Drozer while
  adding modern C2 features.
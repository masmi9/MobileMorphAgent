# Agent-Server Connection Guide

## Overview

This guide explains how the MobileMorph Agent (Android APK) connects to the Morph Server for Android DAST testing.

---

## Fixes Applied

### CommandService.java Bugs Fixed:

1. **Line 43**: Fixed Socket type from `java.net.Socket` to `io.socket.client.Socket`
2. **Line 205**: Changed `CommandExecutor.execute()` to `ShellExecutor.execute()`
3. **Line 203-210**: Updated command handler to parse JSON format from server
4. **Line 292**: Fixed `mainHandler` typo to `handler`
5. **Line 330-332**: Fixed NotificationChannel/NotificationManager types

---

## Connection Flow

### 1. User Clicks "Start Agent" Button

**MainActivity.java (Line 46-53)**
```java
startAgentButton.setOnClickListener(v -> {
    if (!hasStoragePermissions()) {
        Toast.makeText(this, "Permission required", Toast.LENGTH_SHORT).show();
        return;
    }
    startAgentService();  // <-- Starts CommandService
    Toast.makeText(MainActivity.this, "Agent Started", Toast.LENGTH_SHORT).show();
});
```

### 2. CommandService Starts

**CommandService.java (Line 77-93)**
```java
@Override
public int onStartCommand(Intent intent, int flags, int startId) {
    // 1. Create foreground notification
    createNotificationChannelIfNeeded();
    Notification notification = buildPersistentNotification();
    startForeground(NOTIF_ID, notification);

    // 2. Register device with server (HTTP POST)
    new Thread(this::registerWithServer).start();

    // 3. Setup WebSocket connection
    new Thread(() -> setupWebSocket(SERVER_URL, deviceId)).start();

    return Service.START_STICKY;
}
```

### 3. HTTP Registration

**CommandService.java (Line 241-272)**
- POSTs to `http://192.168.6.198:5000/register`
- Sends device metadata (device_id, manufacturer, rooted status)
- Server stores agent in `connected_agents` dictionary

### 4. WebSocket Connection Established

**CommandService.java (Line 121-227)**

#### Connection Setup:
```java
IO.Options opts = new IO.Options();
opts.reconnection = true;
opts.reconnectionAttempts = Integer.MAX_VALUE;
opts.reconnectionDelay = 1000;
opts.reconnectionDelayMax = 60000;

mSocket = IO.socket(serverUrl, opts);
```

#### Event Handlers:

**EVENT_CONNECT (Line 149-167)**
```java
mSocket.on(Socket.EVENT_CONNECT, new Emitter.Listener() {
    @Override
    public void call(Object... args) {
        Log.i("WS", "Connected to C2 server");

        // Emit registration event
        JSONObject payload = new JSONObject();
        payload.put("device_id", deviceId);
        payload.put("manufacturer", Build.MANUFACTURER);
        payload.put("model", Build.MODEL);
        payload.put("rooted", checkRootAccess());
        mSocket.emit("register", payload);
    }
});
```

**COMMAND EVENT (Line 197-218)** - Fixed!
```java
mSocket.on("command", new Emitter.Listener() {
    @Override
    public void call(Object... args) {
        JSONObject cmdData = (JSONObject) args[0];  // Parse JSON
        String cmd = cmdData.getString("cmd");
        Log.d("WS", "Received command: " + cmd);

        // Execute command via ShellExecutor
        String result = ShellExecutor.execute(cmd);

        // Send result back to server
        JSONObject respPayload = new JSONObject();
        respPayload.put("device_id", deviceId);
        respPayload.put("result", result);
        mSocket.emit("command_result", respPayload);
    }
});
```

### 5. Server Side Handling

**main.py (Line 366-372)** - Receives registration
```python
@socketio.on('register')
def register_agent(data):
    device_id = data.get("device_id")
    register_device(device_id, data)
    agent_sockets[device_id] = request.sid  # Store socket ID
    emit('agent_list', connected_agents, broadcast=True)
    print(f"[+] WebSocket Agent registered: {device_id}")
```

**main.py (Line 390-400)** - Send commands
```python
@socketio.on('send_command')
def send_command(data):
    device_id = data.get("device_id")
    command = data.get("command")
    args = data.get("args", {})

    if device_id and command:
        command_queue[device_id] = command
        sid = agent_sockets.get(device_id)
        if sid:
            emit('command', {'cmd': command, 'args': args}, to=sid)
        print(f"[>] Sent to {device_id}: {command}")
```

**main.py (Line 379-388)** - Receive results
```python
@socketio.on('command_result')
def on_command_result(data):
    device_id = data.get("device_id")
    result = data.get("result")
    print(f"[<] Output from {device_id}:\n{result}")
    result_store[device_id] = result
```

---

## Testing the Connection

### Step 1: Start the Server

```bash
cd C:\Users\MalikSmith\repos\Malik_MobileMorph_Project\MobileMorphAgent\morph_server\server
python main.py
```

**Expected Output:**
```
 * Running on http://0.0.0.0:5000
```

### Step 2: Update SERVER_URL in Agent

Edit `CommandService.java` line 41:
```java
private static final String SERVER_URL = "http://YOUR_COMPUTER_IP:5000";
```

Find your IP:
```bash
# Windows
ipconfig | findstr IPv4

# Linux/WSL
ip addr show | grep inet
```

### Step 3: Build and Install Agent

```bash
cd C:\Users\MalikSmith\repos\Malik_MobileMorph_Project\MobileMorphAgent\android_agent

# Build APK
gradlew assembleDebug

# Install on device
adb install app\build\outputs\apk\debug\app-debug.apk
```

### Step 4: Start Agent on Device

1. Open MobileMorph Agent app
2. Grant storage permission if requested
3. Click "Start Agent" button

**Expected MainActivity logs:**
```
D/MainActivity: Starting agent service...
I/CommandService: startForeground() called
I/CommandService: setupWebSocket: connecting to http://192.168.6.198:5000
I/CommandService: setupWebSocket: mSocket.connect() called
```

**Expected Server logs:**
```
[✓] Agent connected via WebSocket
[+] Registered Agent: abc123def456 {'manufacturer': 'Google', 'model': 'Pixel 7', 'rooted': False, 'last_seen': 1234567890}
[+] WebSocket Agent registered: abc123def456
```

### Step 5: Send Test Command

**Via Web Dashboard:**
1. Open `http://localhost:5000` in browser
2. Find your device in agent list
3. Send command: `ls -la /sdcard`

**Via API:**
```bash
curl -X POST http://localhost:5000/api/send_command \
  -H "Content-Type: application/json" \
  -d '{"device_id": "YOUR_DEVICE_ID", "command": "ls -la /sdcard", "args": {}}'
```

**Expected Agent logs:**
```
D/WS: Received command: ls -la /sdcard
```

**Expected Server logs:**
```
[>] Sent to abc123def456: ls -la /sdcard
[<] Output from abc123def456:
drwxrwx--x 12 root sdcard_rw 4096 2025-01-13 10:30 .
drwxr-x--x  6 root root      4096 2025-01-01 00:00 ..
...
```

---

## Troubleshooting

### Agent Shows "Agent Started" but No Server Connection

**Problem:** WebSocket not connecting

**Check:**
1. Server is running on correct IP/port
2. Firewall allows port 5000
3. Device can reach server IP (test with `ping` or browser)
4. Check logcat for connection errors:
```bash
adb logcat | grep -E "(CommandService|WS)"
```

**Common Errors:**
- `Connection error: unknown/no-arg` - Server not reachable
- `Connection timeout` - Firewall blocking or wrong IP

### Server Receives Connection but No Registration

**Problem:** Agent connects but doesn't emit registration

**Check:**
1. Agent logcat shows: `Connected to C2 server`
2. But server doesn't show: `[+] WebSocket Agent registered`

**Fix:** Check if device_id is null or JSON building fails

### Commands Not Executing

**Problem:** Server sends command but agent doesn't respond

**Check:**
1. Server logs show: `[>] Sent to device_id: command`
2. Agent logs should show: `Received command: command`
3. If not, check socket event handler

**Before fix:** Agent expected String, server sent JSON
**After fix:** Agent parses JSON correctly

---

## Connection State Diagram

```
[User Clicks Button]
    ↓
[MainActivity.startAgentService()]
    ↓
[CommandService.onStartCommand()]
    ↓
    ├─→ [HTTP POST /register] → [Server stores agent metadata]
    │
    └─→ [WebSocket connect]
            ↓
        [EVENT_CONNECT fires]
            ↓
        [Emit 'register' event with device info]
            ↓
        [Server receives 'register']
            ↓
        [Server stores socket ID in agent_sockets]
            ↓
        ✅ [Agent Ready - Can receive commands]

[Dashboard/API sends command]
    ↓
[Server emits 'command' to agent socket]
    ↓
[Agent receives 'command' event]
    ↓
[ShellExecutor.execute(cmd)]
    ↓
[Agent emits 'command_result']
    ↓
[Server receives result]
    ↓
✅ [Result stored in result_store]
```

---

## Network Security Configuration

The agent has network security config at:
`android_agent/app/src/main/res/xml/network_security_config.xml`

For testing with HTTP (not HTTPS), ensure cleartext traffic is allowed:
```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>
```

---

## Advanced: Debugging WebSocket Connection

### Enable Verbose Socket.IO Logging

Add to CommandService.java:
```java
import java.util.logging.Logger;
import java.util.logging.Level;

// In setupWebSocket():
Logger.getLogger("io.socket").setLevel(Level.FINE);
```

### Monitor Network Traffic

Use Charles Proxy or Wireshark to see WebSocket frames.

### Check Connected Agents API

```bash
curl http://localhost:5000/agents
```

Should show your agent with `"online": true`

---

## Next Steps

Once connection is working:

1. **Test exploit modules** - `/exploit/<module>` endpoints
2. **Push Frida hooks** - `/frida_hooks` endpoint
3. **Load DEX payloads** - Dynamic code loading
4. **Integrate with DYNA** - `/run_dyna` endpoint for OWASP scans

---

## Summary

✅ **Fixed Issues:**
- Command handler JSON parsing
- ShellExecutor reference
- Socket type declaration
- Handler variable name
- NotificationChannel types

✅ **Connection Works:**
1. User clicks "Start Agent"
2. Service starts, registers via HTTP
3. WebSocket connects and emits registration
4. Server stores socket ID
5. Commands can be sent and results received

🎯 **Ready for Android DAST Testing!**

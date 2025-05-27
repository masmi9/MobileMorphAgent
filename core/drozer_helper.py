import requests
import time

class DrozerHelper:
    def __init__(self, device_id: str, server_url: str = "http://127.0.0.1:5000"):
        self.device_id = device_id
        self.server_url = server_url
        self.last_command = None

    def start_drozer(self):
        print(f"[+] Starting MobileMorphAgent test session for {self.package_name} (WebSocket Mode)")
        time.sleep(1) # Simulation connection delay

    def check_connection(self):
        try:
            response = requests.get(f"{self.server_url}/agents")
            return response.status_code == 200 and any(agent["device_id"] == self.device_id for agent in response.json())
        except Exception as e:
            print(f"[!] Connection check failed: {e}")
            return False
    
    def run_command(self, cmd: str):
        try:
            # Send command to server
            print(f"[>] Sending command to agent {self.device_id}: {cmd}")
            r = requests.post(f"{self.server_url}/set_command", json={
                "device_id": self.device_id,
                "command": cmd
            })
            if r.status_code != 200:
                return f"[!] Failed to send command: {r.text}"
            print(f"[→] Sent command: {cmd}")
            # Poll for result (up to 10 seconds)
            for _ in range(30):  # wait max ~15 seconds
                res = requests.get(f"{self.server_url}/agents")
                agents = res.json()
                agent = next((a for a in agents if a["device_id"] == self.device_id), None)
                if agent:
                    output_res = requests.get(f"{self.server_url}/outputs")
                    output = output_res.json().get(self.device_id)
                    if output and output != self.last_command:
                        self.last_command = output
                        return output
                time.sleep(0.5)
            return "[!] Timeout waiting for agent response."
        except Exception as e:
            return f"[!] Error: {e}"
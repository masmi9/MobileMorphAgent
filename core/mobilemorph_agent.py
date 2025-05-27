import requests
import time

class AgentClient:
    def __init__(self, base_url, device_id):
        self.base_url = base_url
        self.device_id = device_id

    def run_command(self, command: str) -> str:
        requests.post(f"{self.base_url}/set_command", json={
            "device_id": self.device_id,
            "command": command
        })
        # Poll for result
        for _ in range(10):
            time.sleep(2)
            resp = requests.get(f"{self.base_url}/results/{self.device_id}")
            if resp.status_code == 200:
                data = resp.json()
                if "output" in data:
                    return data["output"]
        return "No output received"

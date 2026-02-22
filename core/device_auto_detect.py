"""
Auto-detect ADB devices and match with MobileMorphAgent

Automatically runs when dyna.py starts to detect connected devices
and display agent status without requiring manual --device argument.
"""

import subprocess
import requests
import logging

logger = logging.getLogger(__name__)


def get_adb_device() -> tuple:
    """
    Get the ADB-connected device serial and Android ID.

    Returns:
        (adb_serial, android_id) or (None, None) if not found
    """
    try:
        # Get ADB devices
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None, None

        # Parse devices
        lines = result.stdout.strip().split('\n')
        devices = []

        for line in lines[1:]:
            if '\tdevice' in line:
                devices.append(line.split('\t')[0])

        if len(devices) == 0:
            return None, None

        if len(devices) > 1:
            logger.warning(f"Multiple ADB devices found: {devices}. Using first one: {devices[0]}")

        adb_serial = devices[0]

        # Get Android ID from device
        result = subprocess.run(
            ["adb", "-s", adb_serial, "shell", "settings", "get", "secure", "android_id"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            android_id = result.stdout.strip()
            return adb_serial, android_id

        return adb_serial, None

    except Exception as e:
        logger.debug(f"ADB detection failed: {e}")
        return None, None


def check_agent_status(device_id: str, server_url: str) -> dict:
    """
    Check if agent is connected and online for given device ID.

    Returns:
        dict with agent info or empty dict if not found
    """
    try:
        response = requests.get(f"{server_url}/agents", timeout=3)
        if response.status_code == 200:
            agents = response.json()
            for agent in agents:
                if agent.get('device_id') == device_id:
                    return agent
        return {}
    except:
        return {}


def auto_detect_device(server_url: str = "http://127.0.0.1:5000") -> tuple:
    """
    Auto-detect device and return device_id with status info.

    Returns:
        (device_id, device_info_dict) or (None, None)
    """
    adb_serial, android_id = get_adb_device()

    if not android_id:
        return None, None

    # Check agent status
    agent_info = check_agent_status(android_id, server_url)

    device_info = {
        'adb_serial': adb_serial,
        'android_id': android_id,
        'agent_connected': bool(agent_info),
        'agent_online': agent_info.get('online', False) if agent_info else False,
        'model': agent_info.get('model', 'Unknown'),
        'manufacturer': agent_info.get('manufacturer', 'Unknown'),
        'rooted': agent_info.get('rooted', 'Unknown')
    }

    return android_id, device_info


def display_device_banner(device_info: dict) -> None:
    """Display device and agent status banner."""
    print("\n" + "="*60)
    print("📱 Device & Agent Detection")
    print("="*60)
    print(f"ADB Serial:    {device_info['adb_serial']}")
    print(f"Device ID:     {device_info['android_id']}")
    print(f"Model:         {device_info['manufacturer']} {device_info['model']}")

    if device_info['agent_online']:
        print(f"Agent Status:  ✓ Online and ready")
        print(f"Rooted:        {device_info['rooted']}")
    elif device_info['agent_connected']:
        print(f"Agent Status:  ⚠ Connected but offline")
    else:
        print(f"Agent Status:  ✗ Not connected")
        print("               Please start MobileMorphAgent on the device")

    print("="*60 + "\n")

import hmac
import hashlib
import os
import base64
from typing import Dict

# Shared secret should be the same on both server and agent
SHARED_SECRET_KEY = b"MobileMorphSecret"
device_tokens: Dict[str, str] = {}

def generate_signature(agent_id: str) -> str:
    """Generate HMAC SHA-256 signature for a given agent ID."""
    return hmac.new(SHARED_SECRET_KEY, agent_id.encode(), hashlib.sha256).hexdigest()

def generate_token(device_id: str, secret_key: str = None) -> str:
    """
    Generate a secure HMAC token for a given device ID.
    """
    if secret_key is None:
        secret_key = os.environ.get("MORPH_SHARED_SECRET", "changeme")
    token_bytes = hmac.new(secret_key.encode(), device_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(token_bytes).decode()

def register_token(device_id: str, secret_key: str = None) -> str:
    """
    Register a new token for a device and store it.
    """
    token = generate_token(device_id, secret_key)
    device_tokens[device_id] = token
    return token

def verify_signature(provided_signature: str, device_id: str) -> bool:
    """
    Verify HMAC token from agent matches registered device token.
    """
    expected = generate_signature(device_id)
    if not expected:
        return False
    return hmac.compare_digest(expected, provided_signature)

def rotate_token(device_id: str, secret_key: str = None) -> str:
    """
    Force token regeneration for a device.
    """
    return register_token(device_id, secret_key)

def get_device_token(device_id: str) -> str:
    return device_tokens.get(device_id)

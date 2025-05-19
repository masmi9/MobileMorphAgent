import hmac
import hashlib

# This should match the agent's key in Java
SHARED_SECRET_KEY = b"MobileMorphSecret"

def generate_signature(agent_id: str) -> str:
    """Generate HMAC SHA-256 signature for a given agent ID."""
    return hmac.new(SHARED_SECRET_KEY, agent_id.encode(), hashlib.sha256).hexdigest()

def verify_signature(agent_id: str, provided_signature: str) -> bool:
    """Verify agent's signature."""
    expected = generate_signature(agent_id)
    return hmac.compare_digest(expected, provided_signature)

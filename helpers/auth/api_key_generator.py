import hashlib
import secrets
from uuid import uuid4

def generate_api_key() -> tuple[str, str, str]:
    """
    Generates a new API key along with its public identifier and its hash.

    Returns:
        tuple[str, str, str]: (plaintext_key, key_id, key_hash)
            - plaintext_key: the actual secret, shown to the caller only once.
            - key_id: public, non-secret identifier used to list/revoke the key.
            - key_hash: SHA-256 hex digest of the plaintext key, persisted for verification.
    """
    plaintext_key = f"inv_{secrets.token_urlsafe(32)}"
    key_id = str(uuid4())
    key_hash = hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()

    return plaintext_key, key_id, key_hash

def hash_api_key(plaintext_key: str) -> str:
    """Hashes a plaintext API key using SHA-256, for lookup/verification purposes."""
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()
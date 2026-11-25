import hashlib
import hmac


def sign(secret: str, body: bytes) -> str:
    """Return the X-Hub-Signature-256 value for a body (used by senders and tests)."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    """Constant-time check of the GitHub-style sha256 signature header."""
    if not header:
        return False
    return hmac.compare_digest(sign(secret, body), header.strip())

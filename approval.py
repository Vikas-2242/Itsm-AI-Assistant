"""Short-lived signed approval tokens for the demo write path."""
import hashlib, hmac, os, time

_SECRET = os.getenv("APPROVAL_SIGNING_SECRET", "local-demo-only-change-this-secret").encode()
_SECRET = os.getenv(
    "APPROVAL_SIGNING_SECRET",
    "local-demo-only-change-this-secret",
).encode()

print(
    "APPROVAL_SECRET_CONFIGURED:",
    bool(os.getenv("APPROVAL_SIGNING_SECRET")),
)

TTL_SECONDS = 300 # changes
TTL_SECONDS = 300


def issue_token(incident_id: str, operation: str, value: str) -> str:
    expires = int(time.time()) + TTL_SECONDS
    payload = f"{incident_id}|{operation}|{value}|{expires}"
    signature = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def verify_token(token: str, incident_id: str, operation: str, value: str) -> bool:
    try:
        expires_s, signature = token.split(".", 1)
        expires = int(expires_s)
    except (ValueError, AttributeError):
        return False
    if expires < int(time.time()) or expires > int(time.time()) + TTL_SECONDS + 5:
        return False
    payload = f"{incident_id}|{operation}|{value}|{expires}"
    expected = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)

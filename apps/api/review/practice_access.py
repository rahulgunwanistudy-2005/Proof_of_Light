"""Short-lived credentials restricted to the review steps of a practice case."""

import hashlib
import hmac
import re
import secrets
import time

from fastapi import HTTPException

PREFIX = "public-practice:"
LIFETIME = 3600
SECRET = secrets.token_bytes(32)


def practice_actor(nonce: str) -> str:
    return PREFIX + hashlib.sha256(nonce.encode()).hexdigest()


def issue_practice(expires: int) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(32)
    payload = f"{nonce}.{expires}"
    signature = hmac.digest(SECRET, payload.encode(), "sha256").hex()
    return f"{payload}.{signature}", practice_actor(nonce)


def authenticate_practice(token: str) -> str:
    match = re.fullmatch(r"([A-Za-z0-9_-]{43})\.(\d{1,12})\.([a-f0-9]{64})", token, re.ASCII)
    if match:
        nonce, expires, signature = match.groups()
        expected = hmac.digest(SECRET, f"{nonce}.{expires}".encode(), "sha256").hex()
        if hmac.compare_digest(signature, expected) and int(expires) > time.time():
            return practice_actor(nonce)
    raise HTTPException(401, "This practice session has expired. Start a new practice case.")

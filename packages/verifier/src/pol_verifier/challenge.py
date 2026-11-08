"""Phase 0 challenge format. Local server is the issuance authority."""

import hashlib
import hmac
import json
import secrets
import time

PALETTE = {
    "white": [192, 192, 192],
    "dark": [88, 88, 88],
    "red": [194, 117, 125],
    "green": [113, 169, 140],
    "blue": [116, 143, 193],
    "yellow": [185, 172, 108],
}
CALIBRATION = list(PALETTE)
BODY_COLORS = ["red", "green", "blue", "yellow"]


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def issue(secret: bytes, reduced: bool = False) -> dict:
    palette = {
        name: [round((c + 150) / 2) for c in rgb] if reduced else rgb
        for name, rgb in PALETTE.items()
    }
    challenge = {
        "version": "spike-1",
        "id": secrets.token_urlsafe(18),
        "claim_id": "physics-experiment-only",
        "issued_at": time.time(),
        "ttl_s": 120,
        "slot_ms": 650 if reduced else 400,
        "lead_ms": 300 + secrets.randbelow(601),
        "calibration": CALIBRATION,
        "body": [secrets.choice(BODY_COLORS) for _ in range(10)],
        "palette": palette,
        "reduced": reduced,
    }
    challenge["signature"] = hmac.new(secret, canonical(challenge), hashlib.sha256).hexdigest()
    return challenge


def authentic(challenge: dict, secret: bytes) -> bool:
    payload = {k: v for k, v in challenge.items() if k != "signature"}
    expected = hmac.new(secret, canonical(payload), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, challenge.get("signature", ""))

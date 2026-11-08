import base64
import io
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.main import CAPTURES, CHALLENGES, ISSUANCE, app


@pytest.fixture
def client():
    CHALLENGES.clear()
    CAPTURES.clear()
    ISSUANCE.clear()
    with TestClient(app) as client:
        yield client


def capture_body(challenge):
    output = io.BytesIO()
    Image.new("RGB", (160, 120), (140, 140, 140)).save(output, format="JPEG")
    frame = base64.b64encode(output.getvalue()).decode()
    return {
        "challenge": challenge,
        "frames": [frame] * 230,
        "times_ms": [i * 33.33 for i in range(230)],
        "paint_ms": [500 + i * 400 for i in range(17)],
    }


def test_capture_export_reproducible_and_single_use(client):
    challenge = client.post("/api/challenges", json={}).json()
    body = capture_body(challenge)
    response = client.post("/api/captures", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["report"]["verdict"] == "FAILED"  # Identical frames, real integrity rejection.
    downloaded = client.get(result["download"])
    assert downloaded.status_code == 200
    with np.load(io.BytesIO(downloaded.content), allow_pickle=False) as data:
        assert data["frames"].shape == (230, 120, 160, 3)
    assert client.post("/api/captures", json=body).status_code == 409


def test_tampered_challenge_is_rejected(client):
    challenge = client.post("/api/challenges", json={}).json()
    challenge["body"][0] = "purple"
    assert client.post("/api/captures", json=capture_body(challenge)).status_code == 400


def test_expired_challenge_is_rejected(client):
    import hashlib
    import hmac

    from pol_verifier.challenge import canonical

    from apps.api.main import SECRET

    challenge = client.post("/api/challenges", json={}).json()
    challenge["issued_at"] = time.time() - 121
    del challenge["signature"]
    challenge["signature"] = hmac.new(SECRET, canonical(challenge), hashlib.sha256).hexdigest()
    CHALLENGES[challenge["id"]]["challenge"] = challenge
    assert client.post("/api/captures", json=capture_body(challenge)).status_code == 400


def test_cross_origin_upload_and_bad_host_are_blocked(client):
    assert (
        client.post(
            "/api/challenges", json={}, headers={"Origin": "https://other.example"}
        ).status_code
        == 403
    )
    assert client.get("/", headers={"Host": "other.example"}).status_code == 400


def test_reduced_mode_keeps_uniform_four_color_body(client):
    challenge = client.post("/api/challenges", json={"reduced": True}).json()
    assert challenge["slot_ms"] == 650
    assert len(challenge["body"]) == 10
    assert set(challenge["body"]) <= {"red", "green", "blue", "yellow"}


def test_malformed_frame_is_explained(client):
    challenge = client.post("/api/challenges", json={}).json()
    body = capture_body(challenge)
    body["frames"][3] = "not-jpeg"
    assert client.post("/api/captures", json=body).status_code == 422


def test_start_rate_limit(client):
    for _ in range(20):
        assert client.post("/api/challenges", json={}).status_code == 200
    assert client.post("/api/challenges", json={}).status_code == 429

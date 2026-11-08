"""Authorized local red-team probe: forge camera frames after challenge issuance.

No camera, real object, LLM, PayPal call, or payment is involved. Synthetic pixels
are explicitly labeled. This tests a real weakness in an untrusted browser upload.
Only loopback destinations are accepted. It is not a physical evaluation fixture.
"""

import argparse
import base64
import io
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx
import numpy as np
from PIL import Image


def probe(url: str) -> dict:
    if urlparse(url).hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("This probe is restricted to your local experiment server")
    with httpx.Client(base_url=url, timeout=30) as client:
        response = client.post("/api/challenges", json={})
        response.raise_for_status()
        challenge = response.json()
        colors = challenge["calibration"] + challenge["body"]
        paint = challenge["lead_ms"] + np.arange(len(colors) + 1) * challenge["slot_ms"]
        times = np.arange(0, paint[-1] + 600, 1000 / 30)
        indices = np.clip(np.searchsorted(paint, times - 120, side="right") - 1, 0, 15)
        rng = np.random.default_rng(2026)
        frames = []
        for index in indices:
            frame = np.full((120, 160, 3), 110.0)
            stimulus = np.array(challenge["palette"][colors[index]])
            frame[20:104, 28:136] += 0.55 * (stimulus - 145) * np.array([1, 0.92, 0.85])
            frame += rng.normal(0, 1.2, frame.shape)
            output = io.BytesIO()
            Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(
                output, "JPEG", quality=85
            )
            frames.append(base64.b64encode(output.getvalue()).decode())
        response = client.post(
            "/api/captures",
            json={
                "challenge": challenge,
                "frames": frames,
                "times_ms": times.tolist(),
                "paint_ms": paint.tolist(),
                "conditions": {
                    "source": "SYNTHETIC_INJECTION_NO_CAMERA",
                    "attack": "adaptive-render",
                },
                "device_meta": {"camera_used": False, "timestamps": "fabricated"},
            },
        )
        response.raise_for_status()
        result = response.json()
    return {
        "experiment": "untrusted-client adaptive synthetic injection",
        "camera_used": False,
        "physical_fixture": False,
        "verdict": result["report"]["verdict"],
        "matches": result["report"]["matches"],
        "chance_p": result["report"]["chance_p"],
        "correlation": result["report"]["correlation"],
        "analysis_ms": result["report"]["elapsed_ms"],
        "security_result": "BYPASS"
        if result["report"]["verdict"] == "VERIFIED"
        else "NOT_ACCEPTED",
        "interpretation": "A signed one-time challenge does not attest the source of uploaded frames.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = probe(args.url)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered)

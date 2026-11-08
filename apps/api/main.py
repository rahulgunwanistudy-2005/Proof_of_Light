"""Local-only Phase 0 server. No PayPal, AI, durable storage or production claims.

FastAPI/Pydantic reference: https://fastapi.tiangolo.com/tutorial/body/
"""

import base64
import io
import json
import secrets
import threading
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pol_verifier.challenge import authentic, issue
from pol_verifier.engine import verify
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="Proof of Light physics spike", version="0.0.1")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
SECRET = secrets.token_bytes(32)
LOCK = threading.Lock()
CHALLENGES: dict[str, dict] = {}
CAPTURES: dict[str, tuple[float, bytes, dict]] = {}
ISSUANCE: dict[str, list[float]] = {}
MAX_UPLOAD = 16 * 1024 * 1024


@app.middleware("http")
async def local_limits(request: Request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return Response("Use the capture page on this server.", status_code=403)
        # Count streamed bytes rather than trusting a supplied Content-Length.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_UPLOAD:
                return Response("Capture exceeds the 16 MB upload limit.", status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'"
    )
    return response


def cleanup():
    now = time.time()
    for key, value in list(CHALLENGES.items()):
        if now > value["challenge"]["issued_at"] + 120:
            del CHALLENGES[key]
    for key, value in list(CAPTURES.items()):
        if now > value[0] + 600:
            del CAPTURES[key]
    for key, values in list(ISSUANCE.items()):
        ISSUANCE[key] = [stamp for stamp in values if stamp > now - 60]
        if not ISSUANCE[key]:
            del ISSUANCE[key]


class Start(BaseModel):
    reduced: bool = False


class Capture(BaseModel):
    challenge: dict
    frames: list[str] = Field(min_length=30, max_length=500)
    times_ms: list[float] = Field(min_length=30, max_length=500)
    paint_ms: list[float] = Field(min_length=17, max_length=17)
    device_meta: dict = Field(default_factory=dict)
    conditions: dict = Field(default_factory=dict)


@app.get("/health")
def health():
    return {"status": "ok", "phase": 0, "physical_gate": "pending", "paypal": "not integrated"}


@app.post("/api/challenges")
def start(body: Start, request: Request):
    with LOCK:
        cleanup()
        key = request.client.host if request.client else "unknown"
        recent = ISSUANCE.setdefault(key, [])
        if len(recent) >= 20 or len(CHALLENGES) >= 100:
            raise HTTPException(429, "Too many starts. Wait a minute and try again.")
        recent.append(time.time())
        challenge = issue(SECRET, body.reduced)
        CHALLENGES[challenge["id"]] = {"challenge": challenge, "used": False}
        return challenge


def decode_and_verify(body: Capture):
    if len(body.frames) != len(body.times_ms):
        raise ValueError("Every frame needs a timestamp")
    decoded = []
    for encoded in body.frames:
        if len(encoded) > 80_000:
            raise ValueError("Frame exceeds the 80 KB limit")
        raw = base64.b64decode(encoded, validate=True)
        with Image.open(io.BytesIO(raw)) as image:
            if image.width > 320 or image.height > 240 or image.format != "JPEG":
                raise ValueError("Expected JPEG frames no larger than 320 by 240")
            image.load()
            decoded.append(np.asarray(image.convert("RGB").resize((160, 120))))
    frames = np.stack(decoded)
    times = np.array(body.times_ms, dtype=np.float64)
    paint = np.array(body.paint_ms, dtype=np.float64)
    report = verify(frames, times, paint, body.challenge)
    buffer = io.BytesIO()
    # Numeric arrays and Unicode JSON only. No object/pickle arrays.
    # https://numpy.org/doc/stable/reference/generated/numpy.savez_compressed.html
    np.savez_compressed(
        buffer,
        frames=frames,
        times_ms=times,
        paint_ms=paint,
        challenge_json=json.dumps(body.challenge),
        metadata_json=json.dumps({"device": body.device_meta, "conditions": body.conditions}),
        report_json=json.dumps(report, allow_nan=False),
    )
    return buffer.getvalue(), report


@app.post("/api/captures")
async def capture(body: Capture):
    with LOCK:
        cleanup()
        try:
            valid_signature = authentic(body.challenge, SECRET)
        except (TypeError, ValueError):
            valid_signature = False
        record = CHALLENGES.get(body.challenge.get("id", ""))
        if not valid_signature or not record:
            raise HTTPException(
                400, "Challenge expired or belongs to a different server session. Start again."
            )
        if record["used"]:
            raise HTTPException(409, "This challenge was already used. Start a fresh capture.")
        # Reserve before leaving the lock; concurrent requests cannot reuse it.
        record["used"] = True
    try:
        data, report = await run_in_threadpool(decode_and_verify, body)
    except (ValueError, KeyError, TypeError, UnidentifiedImageError) as exc:
        raise HTTPException(
            422, f"Capture could not be read: {exc}. Start a fresh capture."
        ) from exc
    with LOCK:
        while len(CAPTURES) >= 4:
            del CAPTURES[next(iter(CAPTURES))]
        CAPTURES[body.challenge["id"]] = (time.time(), data, report)
    return {
        "id": body.challenge["id"],
        "report": report,
        "download": f"/api/captures/{body.challenge['id']}.npz",
    }


@app.get("/api/captures/{capture_id}.npz")
def download(capture_id: str):
    with LOCK:
        cleanup()
        entry = CAPTURES.get(capture_id)
        if entry is None:
            raise HTTPException(404, "Capture expired. Download within 10 minutes of recording.")
        return Response(
            entry[1],
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="pol-{capture_id}.npz"'},
        )


@app.get("/")
def index():
    return FileResponse(ROOT / "apps/spike/index.html")


app.mount("/static", StaticFiles(directory=ROOT / "apps/spike"), name="static")

# Proof of Light

An experimental light-challenge workbench for item capture. Intended hackathon
pitch: **“Liveness for things, not faces.”**

**Status: Phase 0 only. The physical gate has not passed. A local injection probe
passed the verifier with fabricated frames and no camera. This is not a working
refund-fraud protection system. No PayPal, AI or payment action is connected.**

## What is working

- Explicitly consented front-camera capture and a full-screen color challenge.
- CSPRNG challenge issued at Start, HMAC signed, 120-second TTL, one-time use.
- Six calibration colors, ten secret slots, standard and reduced-intensity modes.
- Frame and approximate paint timing logs on one browser clock.
- Deterministic integrity checks, calibration-only latency alignment and ROI,
  chromaticity decoding, correlation, response heatmap, trace and chromagram.
- `.npz` export and a repeatable offline verifier CLI; no model keys required.
- Tests of synthetic signals, API validation and replay handling; browser QA
  using a fake camera, including 360 px layout, consent, cancel and download.

## Run locally

Requires Python 3.12+. From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Open [the local workbench](http://127.0.0.1:8000) in your own browser. Select
conditions, consent, enable the camera, frame the object and start the capture.
The camera stops after each recording. Download within ten minutes to keep it.

Camera access requires a secure context. A localhost laptop URL works; a plain
HTTP LAN address on a phone does not. See [MDN’s camera requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).
The spike is local only and allows localhost/127.0.0.1 hosts. Phone/public hosting
is intentionally deferred with the rest of the product build.

The screen changes color. Reduced intensity and a non-light alternative are
available. No device-specific flash certification is claimed; see the
[W3C guidance](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html).

## Reproduce the security finding

Keep the server running, then in a second terminal:

```sh
.venv/bin/python scripts/probe_injection.py
```

The script requests a real challenge and submits generated pixels with fabricated
timestamps. It uses no camera. The saved run obtained **VERIFIED, 10/10**, with
correlation **0.9813**. These are one-run results, not population statistics.
See the [machine-readable report](eval/reports/2026-11-08-injection.json).

The chance value `4^-10` is only an independent uniform-guessing null. It says
nothing about an attacker who sees the challenge and generates an adaptive
response. A signed challenge authenticates server issuance, not the source of
uploaded pixels. A printed photo may also reflect the live screen light.
Neither more challenge entropy nor streaming colors alone solves that boundary.

Do not gate refunds on this verifier. Possible next directions are a narrower
capture-assistance tool with merchant review or an investigation of trusted
capture and stronger physical presentation checks. The user must select the
direction before the gated product phases resume.

## Verify and record physical fixtures

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check apps/api packages scripts tests
node --check apps/spike/capture.js
.venv/bin/pol-verify /absolute/path/to/capture.npz --output /tmp/report.json
```

For browser QA, install a Playwright browser and run `scripts/browser_smoke.py`.
It uses fake media only. See [evaluation instructions](docs/EVAL.md) and the
[physical recording checklist](scripts/record_fixture.md). No physical capture
dataset, calibrated thresholds, FAR/FRR or fraud-blocking claim exists yet.

## Scope and planned integrations

The requested system uses PayPal sandbox Orders/Disputes/Payments/Webhooks,
PayPal Agent Toolkit, Gemini damage assessment, and Render durable jobs. These
are **planned, not implemented**. No sponsor integration, hosted judge path,
evidence submission, sandbox dispute or refund is shown as working.

The later design calls for a model to propose a damage assessment, a deterministic
policy to decide, and a gated outbox to act in PayPal. Those components cannot
make the current browser capture authentic by themselves.

See [decisions](docs/DECISIONS.md), [threat model](docs/THREAT_MODEL.md),
[progress](docs/PROGRESS.md), [AI tools used](docs/AI_TOOLS.md) and
[official implementation sources](docs/REFERENCES.md).

## Privacy and license

No microphone, no face requirement, no third-party upload. Up to four captures
remain only in local server memory for ten minutes, removed on a later request,
eviction or server shutdown. Downloaded files remain on your machine until you
delete them. The planned product’s 30-day retention system is not implemented.

Source is MIT licensed. The supplied frontend design skill retains its separate
Apache-2.0 license in `design/frontend-design/LICENSE.txt`.

Conceptual inspiration: screen-illumination face liveness, including
[iProov’s genuine presence approach](https://www.iproov.com/biometric-encyclopedia/genuine-presence-assurance).
This experimental code is independent and makes no equivalent security claim.

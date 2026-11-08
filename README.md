# Proof of Light

Guided item capture and a merchant review boundary for refund claims.

**Clearer captures. Better-informed refund decisions.**

Current product brief: [capture assistance with merchant review](docs/PRODUCT_BRIEF.md).

**Status: local foundation.** Guided capture, the review API and durable approval
records work locally. The sandbox checkout adapter is tested through the real
PayPal SDK with stubbed responses. No real sandbox transaction, AI assessment,
public deployment or refund executor has been completed.

**A light match does not prove authenticity.** An adaptive injected upload passed
without a camera. Weak/failed captures never automatically deny a claim. Every
financial claim action requires explicit merchant review.

## What is working

- Explicitly consented front-camera capture and a full-screen color challenge.
- CSPRNG challenge issued at Start, HMAC signed, 120-second TTL, one-time use.
- Six calibration colors, ten secret slots, standard and reduced-intensity modes.
- Frame and approximate paint timing logs on one browser clock.
- Deterministic integrity checks, calibration-only latency alignment and ROI,
  chromaticity decoding, correlation, response heatmap, trace and chromagram.
- `.npz` export and a repeatable offline verifier CLI; no model keys required.
- Authenticated merchant case/proposal/approval API with version-bound approval,
  stale-case invalidation, rejection, expiry and a durable outbox. Approval saves
  a queued action; it does not execute PayPal.
- SQLAlchemy 2 mappings, Alembic migration and an audit hash chain. SQLite locally;
  Postgres driver and URL support prepared but not integration-tested.
- PayPal Server SDK 2.4.0 checkout adapter, sandbox host enforcement, server-priced
  catalog, stable request IDs, OAuth cache and bounded transient retries. Not
  exposed as public checkout yet.
- Tests of synthetic signals, API validation and replay handling; browser QA
  using a fake camera, including 360 px layout, consent, cancel and download.

## Run locally

Requires Python 3.12+. From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock -e .
.venv/bin/python scripts/init_local.py
.venv/bin/alembic upgrade head
.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Open [the local workbench](http://127.0.0.1:8000) in your own browser. Select
conditions, consent, enable the camera, frame the object and start the capture.
The camera stops after each recording. Download within ten minutes to keep it.

Camera access requires a secure context. A localhost laptop URL works; a plain
HTTP LAN address on a phone does not. See [MDN’s camera requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).
The spike is local only and allows localhost/127.0.0.1 hosts. Phone/public hosting
is not configured yet.

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

The approved direction is capture assistance with merchant-reviewed financial
actions. The light response is diagnostic evidence, never refund authorization
or proof of fraud. The known bypass stays visible and reproducible. See the
[merchant-review contract](docs/MERCHANT_REVIEW.md).

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
PayPal Agent Toolkit, Gemini damage assessment, and Render durable jobs.
Checkout SDK code is implemented and locally stub-tested. Disputes, Payments,
Webhooks, Agent Toolkit, Gemini and Render resources remain planned. No hosted
judge path, evidence submission, real sandbox dispute or refund is shown as
working. APIMatic’s PayPal context package was installed and used to ground the
SDK integration; see the specific evidence in [AI_TOOLS.md](docs/AI_TOOLS.md).

The model will suggest visible damage and uncertainty. A merchant reviews the
exact proposed action; code verifies the approval before an eventual executor
acts in PayPal. These components do not attest camera authenticity.

See [decisions](docs/DECISIONS.md), [threat model](docs/THREAT_MODEL.md),
[progress](docs/PROGRESS.md), [AI tools used](docs/AI_TOOLS.md) and
[official implementation sources](docs/REFERENCES.md).

## Privacy and license

No microphone, no face requirement, no third-party upload. Up to four captures
remain only in local server memory for ten minutes, removed on a later request,
eviction or server shutdown. Downloaded files remain on your machine until you
delete them. Review case, proposal, approval and audit records persist separately
in the local database and have no automatic retention job yet. The planned
product’s 30-day retention system is not implemented.

Source is MIT licensed. The supplied frontend design skill retains its separate
Apache-2.0 license in `design/frontend-design/LICENSE.txt`.

Conceptual inspiration: screen-illumination face liveness, including
[iProov’s genuine presence approach](https://www.iproov.com/biometric-encyclopedia/genuine-presence-assurance).
This experimental code is independent and makes no equivalent security claim.

## Merchant review setup

The first-run helper creates an ignored `.env` without overwriting an existing
file and generates a merchant-only access token. Keep it out of buyer flows,
AI prompts and public demos. Open `/docs` locally and use its Authorize control
with that credential to inspect the review API. Review access is disabled when
the credential is missing or too short. See [review instructions](docs/MERCHANT_REVIEW.md).

Add external sandbox credentials only to `.env`. There is no production PayPal
mode. A completed review still reports `paypal_executed: false` while the executor
is absent. Never present a saved approval as a completed refund.

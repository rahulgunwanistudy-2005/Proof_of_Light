# Architecture

The local app serves capture, shop and review pages from one FastAPI origin. SQLAlchemy and Alembic store invitations, cases, evidence, orders, approvals, action outcomes and the audit chain. SQLite is the local default. The browser flow also passed against PostgreSQL.

Buyer invitations scope one submission to a case. A submitted capture keeps a JPEG and compact report. Gemini notes are opt-in and advisory. The merchant’s bearer credential controls evidence access, PDF export, approval and dispatch. The refund route checks the saved approval and the current PayPal capture before sending an explicitly approved request.

PayPal’s hosted sandbox approval page handles buyer checkout. Signed webhooks and manual imports keep dispute data visible in the console. Dispute resolution takes place in PayPal. The Render Blueprint defines the web service and database.

## Capture path

```text
User browser (untrusted pixels and timing)
  consent -> getUserMedia -> rAF color rendering -> JPEG frame sampling
      |                 ^
      |          POST /api/challenges
      |          server CSPRNG + HMAC + TTL + single-use record
      v
POST /api/captures
  origin/host/size validation -> signature/expiry/single-use check
  -> JPEG decode -> NumPy arrays -> deterministic verifier
  -> provisional report + memory-only NPZ download
                               |
                               v
                      pol-verify offline reanalysis
```

The light-response engine has no web or model dependency. It uses NumPy/SciPy,
chooses latency and response ROI from calibration only, then decodes the ten
secret slots. Browser JSON and exported NPZ use the same engine. API decoding
downsamples to 160x120; the verifier analyzes at most an 80x60 grid.

**Security boundary:** Everything above the POST body is client controlled.
The server can verify its challenge signature but cannot prove how the client
obtained the images. The injection reproduction bypasses that boundary. The result is available as evidence for merchant review.

The original architecture is recorded historically in `BUILD_BRIEF.md`.
`PRODUCT_BRIEF.md` supersedes its autonomous financial policy and security pitch.
See `PROGRESS.md` for the implemented build and remaining verification.

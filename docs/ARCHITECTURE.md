# Architecture

Current direction: capture assistance with mandatory merchant approval. The
local review API stores cases, proposed actions, explicit approvals and an outbox
in SQLAlchemy tables managed by Alembic. Its single-merchant bearer credential
is separate from anonymous capture access. Approval and queue insertion share
a transaction; case edits invalidate queued intent. There is no executor.

The PayPal checkout adapter uses the real SDK against the explicit sandbox host.
It is transport-tested with stubbed responses and is not exposed as a public
checkout endpoint yet. No model, dispute intake or cloud worker is connected.

The capture engine below remains a research measurement, independent of refund
authorization. See `MERCHANT_REVIEW.md` for the approval boundary.

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
obtained the images. The injection reproduction bypasses that boundary. No
PayPal or other external integration consumes the result.

The original architecture is recorded historically in `BUILD_BRIEF.md`.
`PRODUCT_BRIEF.md` supersedes its autonomous financial policy and security pitch.
The full React/Postgres/Render/agent product is not implemented yet.

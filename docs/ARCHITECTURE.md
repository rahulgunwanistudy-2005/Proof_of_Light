# Phase 0 architecture

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

The full requested React/API/Postgres/Render/agent architecture is recorded in
`BUILD_BRIEF.md`. Building it is gated on resolving Phase 0; it is not implemented.

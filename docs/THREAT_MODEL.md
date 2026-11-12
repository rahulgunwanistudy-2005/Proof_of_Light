# Threat model

The question this implementation can measure is whether uploaded pixels follow
the supplied light sequence. It cannot establish that the pixels came from a
trusted camera, that the target is three dimensional, or that the damaged item
is the purchased unit. No autonomous money movement is permitted.

| Input / adversary | Current evidence | Outcome and boundary |
| --- | --- | --- |
| Numerical genuine-like signal, latency, noise, slow drift | Synthetic unit tests | Decodes; validates computation only |
| Old non-adaptive sequence | Synthetic unit test | Wrong body fails; physical replay still needs testing |
| Flat duplicated image bytes | API and verifier tests | Fails duplicate-frame integrity; adding noise defeats that check alone |
| Weak indoor response / bright light | Synthetic weak-response test only | Inconclusive; physical conditions not evaluated |
| Printed image illuminated by this screen | Not physically tested | May pass: paper is a reflecting surface; cannot promise rejection |
| Still/video on another screen | Not physically tested | Must test reflective glare; cannot assume a flat response |
| Adaptive client upload / virtual camera | Actual local HTTP probe with synthetic pixels | **Bypass: VERIFIED, 10/10 without a camera** |
| Fabricated client timestamps | Same local HTTP probe | Accepted as internally consistent; not trusted evidence |
| Changed or reused challenge | API tests | HMAC tampering rejected; second use rejected; does not prevent first-use synthesis |
| Damaged replacement unit plus valid QR | No binding implementation yet | A QR alone does not identify the physical unit |
| Live inpainting of cracks | Not evaluated | Residual risk; no robustness claim |
| Genuine undamaged item | No AI damage model; explicit merchant review required | A light response alone cannot justify a refund |
| Buyer cannot or declines to use lights | Browser UI test | Alternative explains no return/payment action was sent |

## Trust boundaries
The issuance secret belongs to the local server. Challenge sequence, RGB frames,
paint log, device settings and all timestamps are visible to or controlled by the
client. A client signature/HMAC authenticates only what the server signed.
TLS would protect transport, not the honesty of the camera source.

## Physical gate
Pending: 18 genuine recordings (3 objects x 3 lighting setups x 2 devices), and
at least one each of print, screen and replay attacks. Synthetic and fake-camera
browser QA are explicitly excluded. Passing that small test would still not
resolve adaptive injection or prove production FAR/FRR.

## Privacy
Aim the camera at the item and keep faces and personal documents out of the frame. The app requests camera video. Temporary capture bundles expire from memory. When the buyer submits evidence, the server retains a re-encoded JPEG, statement and compact report in the case database. Sending the JPEG and statement to Gemini requires buyer opt-in and a merchant request. Automatic retention remains pending.

## Merchant review
The exact proposal, case revision and authorization are checked again at refund send time. The sandbox order must contain the matching completed capture. The outbox keeps a stable request ID and a unique capture reservation. Interrupted responses are recorded for reconciliation. Payment access uses one merchant credential, kept separate from the buyer invitation. Local PostgreSQL passed the browser practice flow. Live PayPal responses and cloud multi-user operation still need verification.

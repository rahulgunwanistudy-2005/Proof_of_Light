# Decisions

## 2026-11-08: honor the physics gate before the product build
The user's session prompt is the build request. The downloaded pack's evidence
file is source material, not independently verified facts. Its original text is
retained as `docs/research/SUPPLIED_EVIDENCE.md`; do not quote its claims as checked.
Work stops at Phase 0 until the gate and the security assumptions are resolved.
PayPal, Gemini, Render, APIMatic, and Kernel integration code has not begun.

## Phase 0 implementation
A minimal local FastAPI service and plain browser JavaScript reduce time to the
physics experiment. React/Vite and durable database resources remain in Phase 1.
Python 3.12.11 is installed locally. Installed dependency versions are captured
in `requirements-dev.lock`. The server binds only to loopback; there is no public
deployment or use of the user's camera by automation.

## Calibrate yellow explicitly
The brief has four secret colors but only red/green/blue calibration samples.
A nearest-centroid decoder cannot learn a yellow centroid from a missing sample.
Add a sixth calibration slot, yellow. Standard illumination is 16 x 400 ms =
6.4 seconds, plus a 300–900 ms lead-in and 550 ms camera tail. Reduced mode uses
650 ms slots and blends every palette entry halfway toward neutral gray.
Body choices are independent uniform CSPRNG draws; repeated colors are allowed.
Rejecting repeats would reduce the stated 20-bit entropy.

## Exact binomial null and distinct physics threshold
For ten independent uniform guesses, P(at least 10 matches) = 4^-10 =
0.00000095367431640625. Nine matches do not meet p < 1e-6. The experimental
`VERIFIED` verdict therefore requires all ten matches and correlation >= 0.65.
The separate physical gate asks for at least 8/10 in 80% of real captures.
Do not confuse either threshold with a calibrated probability of fraud.
All signal thresholds remain provisional and are not tuned on physical data.

## No authenticity or money claim from a match
On 2026-11-08, the local HTTP red-team probe obtained `VERIFIED` with 10/10
matches using generated frames, fabricated timing logs and no camera. A signed
server challenge and one-time use do not authenticate the client-supplied data.
Serving colors one slot at a time alone would not fix adaptive recoloring of a
video. Waiting the correct duration also would not fix the source of the pixels.
Likewise, paper can reflect changing screen light. QR presence binds a visible
token, not the identity of the physical unit or authenticity of its damage.

Recorded reproduction: `eval/reports/2026-11-08-injection.json`.
No automated refund integration should depend on this experiment. A new product
direction needs the user's choice: capture assistance with merchant review, or
investigation of a trusted capture path and stronger physical presentation checks.
Neither option should be marketed as a proven solution before testing.

## Privacy and scope of the spike
No audio is requested. Captures are held only in process memory, at most four,
with ten-minute expiry checked on the next request; server restart removes all.
Downloads are explicit and contain sampled 160x120 RGB frames, timestamps,
challenge, settings and analysis. No persistent retention policy is implemented.
Frame callbacks use presentation time; this is not a sensor timestamp guarantee.
The spike does not lock exposure, retain full-resolution keyframes, bind an
order QR, estimate damage, attest a physical camera, or perform production auth.

## Photosensitivity language
The UI describes the change rate and offers reduced intensity and an alternative.
No device-specific flash-analysis certificate is claimed. The renderer schedules
from the last actual rAF mutation, preventing missed slots from catching up in
a rapid burst. An rAF mutation log is an approximation of display paint.

## Hosting
The requested production host is Render. Do not create an unrelated Sites
deployment or publish the experimental service while its gate is unresolved.
Phones need a trusted HTTPS origin; a laptop's LAN HTTP address is not sufficient.

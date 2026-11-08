# Physical recordings for the Phase 0 gate

**Current security finding:** synthetic injected frames already bypass this
verifier. Physical recordings can answer whether the optics work; they cannot
repair the trusted-camera problem. Do not buy equipment for this experiment.

## First capture on this laptop
1. Start the server using the README, then open http://127.0.0.1:8000 in your own
   browser. The camera does not start until consent and Enable camera.
2. Use a light-colored mug in normal indoor lighting. Screen faces the item,
   front camera faces the item, distance about 25 cm. Keep your face out of view.
3. Select the surface, lighting and distance. Leave other apps using the camera
   closed. Use reduced mode or the alternative if changing lights are unsuitable.
4. Hold still for about eight seconds in standard mode. Press Escape or Stop
   capture to cancel. Do not move the tab to the background.
5. Read the chromagram and download the NPZ within 10 minutes. The next recording
   needs consent still checked and Enable camera again; the camera stops after
   each recording. Do not publish raw captures without review for personal data.
6. Place files in ignored `eval/fixtures/`; record device, object, light, distance
   and human-attested physical provenance in the manifest below.

## Full matrix (18 genuine captures minimum)
Use ceramic, matte cardboard and plastic. For each, test normal indoor, dim
indoor and bright indirect window light. Repeat all nine on laptop and phone.
Use 15–40 cm consistently and record the actual selection. No full physical
lighting, glossy-surface or device robustness claim can come from one laptop.

Phone camera capture needs a trusted HTTPS origin. The local service currently
allows loopback hosts only; do not use a laptop LAN HTTP URL and expect camera
permission. A phone-accessible deployment or deliberate trusted local HTTPS
setup is a later step after the user chooses how to address the bypass.

| Object | Normal laptop | Dim laptop | Window laptop | Normal phone | Dim phone | Window phone |
| --- | --- | --- | --- | --- | --- | --- |
| Ceramic | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Cardboard | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Plastic | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

## Physical attacks (at least three)
- Print a photograph of the mug. Hold the print where the item would be and
  choose Printed item photo. **A passing result is possible and must be kept.**
- Show the mug photo on a second device. Choose Item photo on a screen. Avoid
  blocking all screen reflection; test the attacker-friendly position too.
- Play an earlier genuine capture on that device under a fresh challenge.
  Choose Earlier video on a screen. Keep the original recording alongside it.

## Manifest format
Create `eval/fixtures/manifest.json` containing entries like:
```json
[
  {
    "path": "ceramic-indoor-laptop.npz",
    "kind": "genuine",
    "object": "ceramic",
    "lighting": "indoor",
    "device": "laptop",
    "attack": null,
    "physical_recording": true
  },
  {
    "path": "print-indoor-laptop.npz",
    "kind": "attack",
    "object": "printed-mug",
    "lighting": "indoor",
    "device": "laptop",
    "attack": "print",
    "physical_recording": true
  }
]
```
Use `screen` and `replay` for the other attacks. Never add generated captures,
Chromium fake-camera data or the injection probe to this physical manifest.
Gate: 8/10 or more in at least 80% of genuine runs, all physical attacks <=4/10.
Keep failures and inconclusive captures; do not discard them to improve the rate.

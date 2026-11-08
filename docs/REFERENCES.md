# Implementation references checked 8 Nov 2026

Official documentation read through Firecrawl before the corresponding API code:

| Source | Used for |
| --- | --- |
| https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia | Secure context, explicit camera permission, audio false, preferred front camera and ideal constraints |
| https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback | Callback scheduling and presentationTime / captureTime clock distinction; rAF fallback limitations |
| https://numpy.org/doc/stable/reference/generated/numpy.savez_compressed.html | Numeric array NPZ export and avoiding pickle/object data |
| https://fastapi.tiangolo.com/tutorial/body/ | BaseModel request body validation; old request-body URL returned 404, official search located the current path |
| https://fastapi.tiangolo.com/tutorial/body-fields/ | Field limits on input lists |
| https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html | Distinguishing opposing flash transitions from color changes; rate constraints and warning against a safety certification claim |

The supplied business/hackathon research is preserved separately and has not
been independently rechecked. No PayPal, Gemini, Render or sponsor API is coded
in Phase 0, so those current contracts have not yet been researched.

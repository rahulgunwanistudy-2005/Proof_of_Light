# Proof of Light design plan

## Phase 0: an optical workbench
The first screen is an experiment, with the chromagram as its single memorable visual. It asks whether a surface follows a fresh light sequence; it must not imply refund eligibility or object authenticity.

## Tokens
- Porcelain `#F5F8FB`: cool, clean light-table background.
- Ink `#203247`: headings and body copy.
- Cobalt `#315BA8`: primary actions and optical instrument accents.
- Steel `#64758A`: borders and quiet graphics; use Ink for small text.
- Glass `#DCE8F4`: framing guide and surface separation.
- Paper `#FFFFFF`: camera surround and reading surfaces.
Challenge colors are experimental stimuli, not brand tokens. Their RGB values are versioned in code.

## Type
Avenir Next where installed, then Segoe UI and system sans for ordinary language. Georgia for the product name and main title, used at moderate size like an instrument maker's nameplate. Tabular numerals for measurements; no monospace labels, all-caps eyebrows or highlighted headline words.

## Layout alternatives
A. Split optical bench: large camera left, narrow recording instructions right, full-width chromagram below. Choose this for quick framing on desktop.

    Proof of Light                      Physics spike
    Test what the light can prove.
    [ Camera / item guide       ] [ Consent & conditions ]
    [                           ] [ Camera / start      ]
    Issued  [ color ][ color ][ color ] ...
    Read    [  ?   ][  ?   ][  ?   ] ...
    Result and experimental limitations

B. Centered wizard: one step at a time. Useful for the later buyer flow, but hides experimental metadata; defer until the physics gate passes.

At 720px and below, put framing instructions and consent before the camera. Left align copy. Show the calibration separately from the ten secret slots. Keep live preview small during illumination so most of the screen remains a light source.

## Principles
- A chromagram is data: every swatch has a text color name and slot number accessible to screen readers.
- No camera starts without consent. No colors change before an explicit Start action.
- No decorative motion. Respect reduced motion outside explicitly consented capture.
- Outcomes say signal matched, wrong signal, or insufficient signal. No claim of fraud detection.
- Keep export and recovery actions visible after errors.

## Review against the supplied design skill (before UI implementation)
Rejected warm cream/clay ceramics branding: it would borrow a generic visual formula and compete with the experimental colors. Revised to cool porcelain and cobalt instrument surfaces. Rejected a tiled dashboard: this phase has one task, so use one bench and a plain instruction rail. Retained a serif only for the name/title, avoiding oversized editorial typography and hairline newspaper columns. No gradients, decorative numbered labels, stock illustrations, shadowed card grid or automatic animation.

## Critiques
Pass 1: inspected desktop, 360px and the fake-camera result. The camera guide
crossed placeholder text on mobile, the status bar inherited an unnecessarily
short paragraph width, and a weak result displayed an empty trace. Removed the
guide until a camera is visible, made status span the bench, and replaced the
empty trace with a specific no-response message. Added the confirmed injection
finding above the bench so a research build cannot imply security it lacks.

Pass 2: inspected revised desktop and mobile screenshots. The hierarchy and
no-overflow behavior held at 360px. Increased consent hit areas, retained a
keyboard-focusable result heading after completion, and moved the result into
view without animation. A keyboard trap keeps Tab on Stop capture while the
light field is open; Escape cancels. No decorative motion was added.

Final screenshots use the final-* prefix. Result screenshots always come from
Chromium fake media and do not establish physical camera performance.

## Claim and merchant workflow

Keep the capture screen's navy, pale blue and paper palette. Use the existing serif headings and system sans for forms. Add two views with the same horizontal navigation. The buyer sees the invitation context, a short statement field, and either the camera or photo upload. The merchant sees a narrow case list beside a wide evidence sheet, then the exact refund destination and amount above the approval controls. On phones these sections stack in reading order. Use the recorded frame and chromagram as the visual anchors. Catalog tiles use color fields and object names until product photography is available. Keep provider status beside the action it affects. This keeps the design centered on evidence and decisions and avoids decorative dashboard cards or metrics.

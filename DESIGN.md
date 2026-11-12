# Proof of Light

The visual reference is [FYNSEC by Phenomenon Studio](https://dribbble.com/shots/20944059-FYNSEC-Website-design-for-cybersecurity-company). The shot uses a charcoal canvas, a warm off-white hero with concave corners, a pill navigation, large sans-serif headlines, dimensional optical artwork, and yellow highlights.

## Application

- Use charcoal `#1b1b1b` for the canvas, `#232323` for cards, and `#484742` for panel borders. Use warm ivory `#f7f4eb` for introductory panels and pale yellow `#f3ff8a` for primary actions and focus. These values are implementation choices based on the screenshot.
- Set headlines in a compact sans-serif with negative tracking and reserve monospaced type for the short hero label. The layout uses Helvetica Neue or the system fallback when Inter is unavailable.
- Build the hero as a two-column panel with an original optical illustration. Continue the ivory surface into the navigation and cut away the lower-right corner for the method link. Stack the artwork below the headline on phones.
- Use thin rules and outlined cards to organize the lab and merchant tools. Keep their inputs, consent, and feedback visible. Use the existing ceramic images for the sandbox catalog and open buyer invitation links directly on the evidence form.

## Dimensional layer

- The hero renders an original WebGL2 scene in `apps/spike/fx/lightstack.js`: a stack of waving evidence layers (foil, chartreuse gel, graphite felt, ember mesh) with a coated camera lens resting on top. It is raw WebGL so the page stays same-origin under the CSP. Without WebGL2 the still `light-optics.webp` image remains.
- The **Light show** toggle in the hero notch tints the scene with the capture palette at the challenge pace (2.5 changes per second, crossfaded rather than flashed) and sweeps the headline colour. It is off by default.
- Isometric layer stacks are pure CSS 3D: inline in the headline, and spinning above each numbered step card. Cards tilt toward the pointer on fine-pointer devices.
- `prefers-reduced-motion` freezes the scene on a single frame, stops the marquee, the spin and the reveals. Inter (OFL) is vendored in `apps/spike/fonts`.

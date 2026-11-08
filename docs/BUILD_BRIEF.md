# SESSION PROMPT — Build "Proof of Light" for the PayPal AI Hackathon (win-grade, end to end)

> Paste this whole file into Claude Code at the root of an empty repo. Put `design/frontend-design/SKILL.md` (shipped in this pack) in the repo before starting. Work autonomously; ask me only for things only I can do (credentials, account logins, phone recordings, the voiceover).

---

## 0. Mission, deadline, non-negotiables

You are the lead engineer, designer and release manager for **Proof of Light**, an entry to the PayPal AI Hackathon (https://paypalaihackathon.devpost.com). The goal is first place plus one sponsor prize. Ship a real, working, hosted system — not a prototype with mocks dressed up as features.

**Hard deadline: Thu 12 Nov 2026, 12:00 PST = Fri 13 Nov 2026, 01:30 IST.** Internal deadline: **Thu 12 Nov, 20:00 IST**, everything submitted. Current time when this session starts: about Sun 8 Nov, midday IST. That is roughly 100 working hours. Budget them with the phase plan in §9 and do not let any phase overrun by more than 25% without cutting scope from the "stretch" list.

Non-negotiables (from the official rules and organiser updates):
1. Uses **PayPal (sandbox only)** and **AI** meaningfully. Both must be impossible to miss in the README, the Devpost text, the "Built With" list and the video.
2. **Public GitHub repo**, OSS license (MIT) visible in the repo About section, all source + run instructions.
3. **Hosted demo that works without judge API keys** (LLM keys server-side). Must stay up, free to use, until **15 Dec 2026**.
4. **Public YouTube video < 3:00** showing the real thing working end to end. No third-party trademarks or copyrighted music. Human voiceover (record it myself; you write the script).
5. Devpost text includes **"AI tools used and how"**.
6. Judges may not run anything: **the video and README carry the score**. Judging may include automated AI analysis of the repo, so the repo must be legible to a machine reader too.
7. Five equal criteria, 1–5 each: Technological Implementation (also the tiebreaker), Design, Potential Impact, Innovation, Presentation.

Honesty rules (the panel is developer advocates and engineers; they will catch theater):
- Nothing simulated is presented as real. Anything simulated is labelled in UI and README.
- Every number in the README/video comes from our own eval runs (reproducible command) or a cited source.
- No look-alike PayPal pages, no fake PayPal emails/receipts. Use PayPal's real sandbox UI where PayPal UI appears.

---

## 1. The product in one paragraph

Buyers now fake "damaged item" evidence with image generators to get refunds while keeping the goods (WIRED, Dec 2025; Forter: AI-doctored refund claims up 15%+; first administrative penalty in China for AI-faked dead crabs; eBay sellers hit Jan 2026). Detectors can't reliably tell. And on PayPal, "significantly not as described" claims are **excluded from Seller Protection**, so the seller eats it. **Proof of Light** flips the question from "is this photo fake?" to "was this filmed right now, of this object, under our light?" When a PayPal dispute arrives, a merchant-side claims agent (built on PayPal's Agent Toolkit plus the dispute tools the toolkit is missing) messages the buyer through the PayPal dispute: *verify the damage on camera for an instant resolution*. The buyer points their phone/laptop camera at the item; the screen flashes a **server-issued, one-time color sequence** (≤ 3 changes/s, photosensitivity-safe); a deterministic photometric verifier checks that the object's reflections carry that exact sequence (an AI fake, a replay or an injected video cannot know it in advance); a vision model assesses the damage against the PayPal order's line items; a deterministic policy engine decides; and the agent resolves the case inside PayPal — offer/refund for verified damage, evidence + escalation for failed or refused verification. Inconclusive never auto-denies: it routes to return-based resolution. In the video, the sandbox-only `adjudicate` endpoint closes both kinds of case live.

Pitch line: **"Proof of Light: liveness for things, not faces."**
Inspiration credit (README): face-liveness by screen illumination (iProov Flashmark, patented for faces). Our implementation is our own and applies the idea to objects and refund claims.

Agentic-commerce line for the pitch (true, one sentence): as AI agents start filing returns and claims for people, someone must prove a human with the real item is present; this is that step for refunds, the way PayPal buyer approval is that step for payments.

---

## 2. Users and the exact before/after

- **Merchant (primary):** Maya runs "Kiln & Ash", a small fictional ceramics shop that takes PayPal. Before: a buyer opens a "not as described" dispute with a convincing cracked-mug photo; she can't prove it's fake, Seller Protection doesn't cover SNAD, she refunds and loses the mug and the money (and pays a dispute fee if it escalates). After: her console shows the dispute arrived, the agent asked for a light-verified capture, the buyer's capture failed the photometric check (or was never done), the agent filed evidence through the Disputes API with the verification report and tracking proof, and PayPal sided with her.
- **Honest buyer (secondary, equally important):** Jordan's mug really arrived cracked. Before: weeks of back-and-forth, return shipping for a broken mug. After: 20-second capture, verified, partial refund lands through PayPal in seconds, no return needed.
- **Fraudster (adversary):** cannot pass, because the color sequence doesn't exist until the capture starts.

---

## 3. System architecture (build exactly this unless you hit a documented blocker)

### 3.1 Stack
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, Postgres (Render Postgres). `httpx` for PayPal REST. numpy, scipy, OpenCV (headless) for the verifier. `pyzbar` or OpenCV QR detector for the order card.
- **Durable pipeline:** **Render Workflows** (Python SDK; public beta, verify current API at render.com docs before coding) for the verification and resolution pipeline: `decode_capture → integrity_checks → photometric_verify → bind_order_card → assess_damage → decide → act_on_paypal → build_evidence_pdf`. Each task idempotent, retried, results persisted. If the Workflows SDK blocks you for > 2 hours, fall back to a Render Background Worker with a Postgres-backed job table (outbox pattern), and record the decision in `docs/DECISIONS.md`.
- **Frontend:** React 18 + Vite + TypeScript, React Router, TanStack Query, plain CSS modules or vanilla-extract with our own tokens (no component kit look). Charts: hand-rolled SVG for the signature visual (see §6); a small lib is fine for secondary charts.
- **AI:** Google Gemini via the official SDK. Use the current best multimodal Flash/Pro model that supports image input + JSON-schema structured output (check https://ai.google.dev for current model IDs; do not guess). Use Gemini's image-editing model for the red-team panel (generating a fake crack on a clean mug photo live). Keep all keys server-side.
- **PayPal:** REST v1/v2 sandbox + **PayPal Agent Toolkit** (Python package; verify name/version on PyPI and github.com/paypal/agent-toolkit) for the claims agent's standard tools; custom tools for what the toolkit lacks. **JS SDK v6** for the demo store checkout.
- **Hosting:** Render — web service (API), static site (frontend), Postgres, Workflows (or worker), cron for the dispute poller. Free/credit tier ($50 hackathon credits: https://credits-portal-mmdm.onrender.com/claim/paypal-ai-hackathon — ask me to claim).
- **Kernel** (cloud browsers, $50 hackathon credits): dispute seeder that logs into the sandbox buyer account and opens disputes in PayPal's sandbox Resolution Center (the create-dispute API needs account-manager scopes; the UI path is self-service). Fallback: I seed manually.
- **APIMatic Context Plugin** (for PayPal Server SDKs): install it in this Claude Code session before writing PayPal integration code, use it for the PayPal API code, and log in `docs/AI_TOOLS.md` exactly where it helped (eligibility for the APIMatic prize requires showing we built the PayPal integration with it).

### 3.2 Repo layout
```
proof-of-light/
  apps/api/            FastAPI app (routers, services, models, paypal/, verifier/, agent/, policy/, evidence/)
  apps/web/            React app: /store (demo shop), /claim/:token (buyer capture), /console (merchant), /lab (red-team + eval)
  workflows/           Render Workflows task definitions
  packages/verifier/   pure-python photometric engine (no web deps) + CLI: `pol-verify capture.npz --challenge ch.json`
  eval/                fixtures/, attacks/, run_eval.py, reports/
  scripts/             seed_disputes_kernel.py, bootstrap_sandbox.py, record_fixture.md
  docs/                ARCHITECTURE.md, THREAT_MODEL.md, EVAL.md, DECISIONS.md, AI_TOOLS.md, SPONSORS.md, VIDEO_SCRIPT.md, DEVPOST.md, research/EVIDENCE.md
  design/              frontend-design/SKILL.md (given), DESIGN_PLAN.md (you write), screenshots/
  .github/workflows/   ci.yml (lint, typecheck, unit tests, verifier tests)
  render.yaml          Blueprint for every Render resource
  LICENSE (MIT), README.md
```

### 3.3 Data model (minimum)
`merchants, orders (paypal_order_id, capture_id, line_items, tracking), disputes (paypal_dispute_id, reason, status, stage, seller_response_due, raw), claims (dispute_id, token, state machine), challenges (id, sequence, issued_at, expires_at, used_at, hmac), captures (challenge_id, frames_ref, device_meta, integrity), verifications (stats json, verdict, artifacts), assessments (model, prompt_hash, output json), decisions (policy_version, inputs_hash, outcome, requires_approval), paypal_actions (outbox: action, request_id, payload, status, response, attempts), audit_log (hash-chained: prev_hash, entry_hash)`.

Claim state machine: `DISPUTE_RECEIVED → INVITE_SENT → CAPTURE_PENDING → CAPTURED → VERIFIED | FAILED | INCONCLUSIVE → DECIDED → ACTION_QUEUED → ACTION_DONE → CLOSED`. Plus `NO_RESPONSE` after a timeout. Illegal transitions raise.

---

## 4. The engine (this is where the 5/5 Technical score is won)

### 4.1 Challenge issuance
- CSPRNG sequence. Structure: **calibration prelude** (known: white, black, red, green, blue — 1 slot each) + **secret body** of N = 10 slots drawn from a 4-color palette chosen for chroma separability (e.g., red, green, blue, yellow; tune in the spike), + random lead-in delay 300–900 ms. Slot length 400 ms → 2.5 changes/s, **below the WCAG 2.3.1 three-flashes-per-second threshold**. Avoid full-saturation red-to-black alternations; keep luminance steps moderate. Run our own HazardTrack/flash-analysis check on the rendered sequence if available, and state the safety rule in the UI.
- Challenge bound to `claim_id`, HMAC-signed, TTL 120 s, single use. The client receives only what it must render, at render time (fetch the sequence at "Start", not earlier).
- Entropy: 10 slots × 2 bits = 20 bits + timing jitter. Report the chance-match probability in the verdict.

### 4.2 Capture client (browser, no app install)
- `getUserMedia` front camera (works on phones and laptops; the screen is what illuminates the object). Guide frame overlay; ask the buyer to hold the item and the **order card** (QR printed on the packing slip; for the demo, printed or shown on a second device) 15–40 cm from the screen, in normal indoor light.
- Full-screen color field with a small live preview inset. Render slots with `requestAnimationFrame`; log the actual paint timestamps.
- Sample frames from the video track (`requestVideoFrameCallback` where supported, else canvas at ~30 fps), each with a capture timestamp on the same clock. Upload downscaled frames (e.g., 320×240 JPEG) + 3 full-res keyframes + the render log + device/track settings (`getSettings()`: resolution, frame rate, whether exposure/white balance are adjustable — try to lock them where the browser allows).
- Photosensitivity notice before start with a "reduced intensity" option (lower contrast palette, longer slots) and an alternative path ("I can't do this — send a return label instead"). Accessible: keyboard operable, screen-reader labels, reduced motion respected outside the challenge itself.

### 4.3 Photometric verifier (`packages/verifier`, deterministic, unit-tested)
1. **Integrity:** timestamp monotonicity, effective fps, duplicate-frame rate, dropped-frame gaps, resolution changes, implausible encoder patterns. Fail closed on gross violations; record soft signals.
2. **Response map:** per pixel (on a downscaled grid), correlate chroma with the calibration prelude to find pixels that actually respond to screen light (near, diffuse surfaces respond; distant background and windows don't). This yields a heatmap — a strong visual for the console and video — and the ROI for the next steps. Exclude clipped pixels.
3. **Signal:** ROI-mean RGB per frame → chromaticity (r/(r+g+b), g/(r+g+b)) to cancel exposure; detrend with a rolling median (~1.5 s) to remove auto-white-balance drift.
4. **Latency alignment:** search camera latency 0–500 ms using the known prelude; then fix it.
5. **Decode:** for each secret slot, take the median chroma displacement over the slot's stable interior; classify to the nearest palette color using per-session centroids learned from the prelude. Compare to the issued sequence → matches k/N. Compute the **binomial chance probability** of ≥k matches with p = 1/4 per slot.
6. **Correlation score:** normalized cross-correlation of the received chroma trace against the expected template, per channel and combined.
7. **Verdict:** `VERIFIED` if k ≥ threshold, chance p < 1e-6 and correlation ≥ τ, with integrity OK; `FAILED` if the signal is present but wrong, or integrity fails; `INCONCLUSIVE` if the response is too weak (e.g., bright sunlight). Thresholds come from the eval (§7), not from vibes; store them versioned in the policy.
8. **Binding:** QR order card detected in ≥ X% of frames; payload = HMAC(order_id) for this dispute's order. Without binding, the most a capture can earn is "item present, not bound to order" → no automatic money movement.
9. Output: a typed `VerificationReport` (all stats, thresholds, versions, artifact paths: trace plot, response heatmap, keyframes) — the same object feeds the console, the evidence PDF and the audit log.

Performance target: verify a 6-second capture in < 2 s on a Render starter instance. Vectorise; no per-pixel Python loops.

### 4.4 Damage assessment (AI, structured)
- Inputs: verified keyframes, the PayPal order's line items (name, description, SKU), optional ship-time reference photo of the unit, the buyer's dispute text.
- Gemini with a strict JSON schema: `item_matches_order (bool, confidence, reason)`, `damage_present`, `damage_type`, `location (bbox)`, `severity (none/cosmetic/functional/destroyed)`, `consistent_with_claim_text`, `notes`. Temperature 0. Log prompt hash, model ID, raw output.
- The model **proposes**; it never moves money.

### 4.5 Policy engine (deterministic, versioned, unit-tested)
Pure function `decide(verification, assessment, order, dispute, merchant_policy) → Decision`. Examples:
- VERIFIED + item matches + functional damage → `accept_claim` with REFUND or `make_offer` REFUND (no return needed) up to the merchant's auto-approve limit; above it → requires merchant approval in the console.
- VERIFIED + cosmetic damage → `make_offer` partial refund per merchant policy %.
- VERIFIED + no visible damage → no refund; `send_message` explaining, offer return-for-refund.
- FAILED (wrong sequence / integrity failure) → `provide_evidence` (verification report + tracking proof of delivery), then `escalate` if still in inquiry.
- INCONCLUSIVE or buyer declined → never deny: `make_offer` REFUND_WITH_RETURN.
- NO_RESPONSE by deadline → `provide_evidence` with tracking + the unanswered invitation.
Every decision lists the rule that fired and the inputs hash.

### 4.6 Claims agent (PayPal Agent Toolkit + custom tools)
- An LLM agent orchestrates the case: reads the dispute (toolkit: list/get dispute, get order/transaction), drafts the buyer invitation in plain language, explains decisions to the merchant, and produces the evidence narrative. It calls **actions only through the policy gate**: the agent proposes an action; the gate checks it equals the policy decision (or is merchant-approved) before it reaches the outbox.
- Custom tools (fill the documented toolkit gap — the toolkit only lists/gets/accepts disputes): `dispute_send_message`, `dispute_make_offer`, `dispute_provide_evidence` (multipart with PDF + images), `dispute_escalate`, `dispute_acknowledge_return`, `sandbox_require_evidence`, `sandbox_adjudicate`, `refund_capture`. Each tool: Pydantic input schema, MCP-style annotations (read-only vs destructive), PayPal-Request-Id idempotency key = hash(dispute_id, action, decision_version).
- Expose the custom tools also as a small MCP server (`apps/api/mcp/`) so other agents can use them; document it. (Stretch: open an upstream issue/PR to paypal/agent-toolkit linking this; only if Phase 8 has time.)

### 4.7 PayPal integration (all real sandbox calls)
- OAuth client-credentials with token caching; one `PayPalClient` with retries (exponential backoff, jitter) on 5xx/429 only, PayPal-Request-Id on every POST, `Prefer: return=representation` where supported, debug-id captured into logs.
- **Demo store** `/store` (Kiln & Ash): JS SDK v6 checkout → Orders v2 create/capture server-side → `POST /v2/checkout/orders/{id}/track` with a carrier + tracking number (status delivered) → each order gets an order card QR.
- **Disputes intake:** webhook `CUSTOMER.DISPUTE.CREATED/UPDATED/RESOLVED` with **signature verification** (`/v1/notifications/verify-webhook-signature`; note simulator events can't be verified — accept them only in an explicitly labelled dev mode). Plus a **poller** (Render cron every 2 min, `GET /v1/customer/disputes` with `update_time_after`) because sandbox webhooks are known to be unreliable — dedupe by dispute id + update_time. Mention this in the README as a deliberate reliability design.
- **Disputes API v1** stage rules (verify against the docs): inquiry stage → send-message, make-offer (REFUND, REFUND_WITH_RETURN, REFUND_WITH_REPLACEMENT, REPLACEMENT_WITHOUT_REFUND), acknowledge-return-item, escalate; claim stage → accept-claim (REFUND, REFUND_WITH_RETURN, PARTIAL_REFUND), provide-evidence. Sandbox-only: `require-evidence` (BUYER_EVIDENCE/SELLER_EVIDENCE) and `adjudicate` (BUYER_FAVOR/SELLER_FAVOR) to close cases on camera; label these "sandbox simulation of PayPal's decision" in the UI.
- **Refunds:** `POST /v2/payments/captures/{id}/refund` (partial supported) for direct resolutions outside a dispute. Use `PayPal-Mock-Response` negative testing on one path to prove the failure handling (e.g., refund declined → outbox retry/alert), and show it in tests, not the video.
- **Constraint:** one dispute per transaction. Pre-stage at least 8 paid, tracked, disputed orders before recording (seeder or manual), distributed across reasons and stages.
- Store all raw PayPal responses (redacted) for the audit trail.

### 4.8 Evidence package
Server-rendered PDF (WeasyPrint or ReportLab): case summary, challenge id + issued sequence vs decoded sequence, chance probability, correlation trace, response heatmap, integrity table, keyframes, tracking proof, policy rule fired, audit hash. Uploaded via provide-evidence. Also downloadable from the console.

---

## 5. Threat model (write `docs/THREAT_MODEL.md`; test each row)
| Attack | Expected result | Why |
|---|---|---|
| AI-edited still photo shown to camera (printed or on a second screen) | FAILED | Flat or wrong chroma response; screens/paper respond differently; no sequence |
| Replay of a genuine earlier capture | FAILED | Different sequence |
| AI-generated video of the item | FAILED | Cannot contain an unknown future sequence |
| Virtual-camera injection of a pre-recorded video | FAILED | Same; plus integrity signals |
| Real-time video manipulation (inpainting cracks live) | Out of scope / residual risk | State honestly; note cost asymmetry and the binding + VLM layers |
| Genuine capture of an undamaged item | VERIFIED + no damage → no refund | Liveness ≠ entitlement |
| Different (damaged) item than the one ordered | item_matches_order false / QR binding fails | Binding layer |
| Bright sunlight / very dark item | INCONCLUSIVE → return-based resolution | Never auto-deny |
| Buyer refuses to verify | REFUND_WITH_RETURN offer | Fairness |
Privacy: no faces needed (aim at the item); frames retained 30 days then deleted; consent screen; data minimisation note.

---

## 6. Design (make it unmistakably not-AI-slop)

Read `design/frontend-design/SKILL.md` first and follow its process literally: write `design/DESIGN_PLAN.md` (4–6 named hex colors, typefaces and roles, layout concepts with ASCII wireframes, principles), review it against the "AI defaults" list in the skill and revise anything generic **before** writing UI code. Then build, screenshot every screen (Playwright), critique, and iterate at least twice.

Subject vocabulary to draw from (choose, don't copy all): photometry, color calibration targets, light tables, evidence lockers, chain of custody, ceramics/kilns (the demo shop). The **one memorable element** is the **chromagram**: a horizontal strip showing the issued color sequence slot by slot, with the decoded reflection drawn beneath it and match/miss per slot — it appears live during capture, on the verdict, in the console, in the PDF and as the video's recurring motif. Everything else stays quiet and disciplined.

Screens:
1. `/` landing: the problem in one sentence, the chromagram as hero (animated once on load, then still), two entry points ("I'm a merchant" → console demo; "Try a claim" → guided capture with a demo order card), and a short "how it decides" section. No stock illustrations, no gradient blobs, no fake logos, no testimonial.
2. `/store`: Kiln & Ash shop with 3 products and real PayPal v6 checkout. Simple and believable.
3. `/claim/:token`: mobile-first capture flow: consent → card + item framing → color challenge (full-screen) → processing (show pipeline steps truthfully as they complete via SSE) → result in plain language.
4. `/console`: merchant inbox (disputes with stage, due date, amount, claim state), case view (timeline of PayPal events + our actions, verification report with chromagram + heatmap, AI assessment with bbox overlay, policy decision with "rule fired", approve/reject, PayPal action log with request IDs and debug IDs, adjudication outcome).
5. `/lab`: red-team panel: (a) generate a fake crack on a clean photo with Gemini live, (b) submit it the "old way" (photo upload) → a naive reviewer accepts, (c) submit through Proof of Light → FAILED with the flat chromagram; plus the eval dashboard (ROC, confusion matrix, per-attack results, n, thresholds, reproducible command).

Quality floor: responsive to 360 px, visible keyboard focus, WCAG AA contrast, `prefers-reduced-motion`, real empty and error states written in plain active voice, no lorem ipsum anywhere.

---

## 7. Evaluation (numbers we can stand behind)
- **Phase 0 spike data becomes the first fixtures.** Then collect: ≥ 40 genuine captures (≥ 4 objects incl. glossy ceramic, matte cardboard, fabric, plastic; ≥ 3 lighting conditions; laptop + phone; 15–40 cm) and ≥ 40 attack captures across the threat model rows (I will record the physical ones; you script the injected/replay/AI-video ones and tell me exactly what to record, with a checklist in `scripts/record_fixture.md`).
- `eval/run_eval.py` → `eval/reports/<date>.md` + JSON: per-condition pass rates, FAR/FRR at the chosen thresholds, ROC/AUC, inconclusive rate, latency p50/p95. Thresholds chosen on a split, reported on held-out captures. Commit the report; the README quotes it verbatim with n.
- Unit tests: verifier on synthetic signals (known sequences + noise + AWB drift + latency), policy table tests (every rule), state machine, idempotency keys, webhook signature handling, PayPal client retries (mocked transport). Contract tests against the real sandbox behind a marker (`-m sandbox`). Frontend: typecheck + Playwright smoke of the four main screens.
- CI green on every push.

---

## 8. Sponsor integration (one sponsor prize can be won; enter where real)
- **Render (primary lane):** API + static site + Postgres + Workflows (or worker) + cron, all from `render.yaml`. In `docs/SPONSORS.md` and the video, show the workflow run view for one case (each task, retries, durations). This is a genuine use: the verification pipeline is a durable multi-step job.
- **APIMatic (secondary lane, cheap):** Context Plugin used to build the PayPal client and dispute tools; record the before/after (e.g., what the agent produced without context vs with it) in `docs/AI_TOOLS.md`. Submit the APIMatic claim form when done (I'll do it).
- **Kernel (no prize, visible craft):** dispute seeder with live view/replay link in the README.
- **AG Grid (stretch only, Phase 8):** if and only if all of Phases 0–7 are done by Wed night IST, add an AG Grid claims desk in `/console` with custom cell renderers (mini chromagram per row, stage chips, due-date countdown) and AG Studio analytics; their judges want custom widgets/theming and the Studio Agent Framework, not a bare grid. Otherwise skip it; a half-done AG integration costs more than it earns.
- Do not add Elastic/Postman/Zapier/Bryntum for decoration.

---

## 9. Phase plan with gates (do not start a phase until the previous gate passes; log each gate result in `docs/PROGRESS.md`)

**Phase 0 — Physics spike (≤ 6 h). KILL GATE.**
Minimal page: front camera + full-screen sequence + frame logging → download `.npz`; Python notebook/CLI computes prelude response, decodes the body, prints k/N and chance p. Test 3 objects × 3 lighting conditions × 2 devices, plus 3 attacks (photo of the item on a second screen, replay, printed photo).
Gate: genuine captures at 15–40 cm indoors decode ≥ 8/10 slots in ≥ 80% of runs AND every attack decodes ≤ 4/10. If the gate fails after tuning (palette, slot length, ROI method, exposure locking), STOP and report to me with data before building anything else.

**Phase 1 — Skeleton + PayPal plumbing (≤ 12 h).** Repo layout, CI, Render Blueprint deployed (hello-world live URL on day 1), Postgres + migrations, PayPal client, demo store with v6 checkout + capture + tracking, webhook + signature verification + poller, Kernel seeder (or manual seeding instructions), 8 disputes staged. Gate: a real sandbox dispute appears in our DB within 2 min of opening it.

**Phase 2 — Verifier engine (≤ 16 h).** Productionise the spike into `packages/verifier` with the full §4.3 pipeline, synthetic tests, fixture tests, CLI, artifacts (trace plot, heatmap). Gate: all tests pass; spike fixtures reproduce; < 2 s per capture.

**Phase 3 — Claims pipeline + agent + policy + PayPal actions (≤ 14 h).** Workflows tasks, state machine, Gemini assessment, policy engine, custom dispute tools + MCP server, outbox with idempotency, evidence PDF, sandbox adjudicate. Gate: end-to-end on the live deployment: real dispute → invite via send-message → capture → verdict → PayPal action → adjudicated; both the honest-buyer and fraudster cases.

**Phase 4 — Frontend (≤ 18 h).** Design plan + review first; then the five screens; SSE progress; screenshots + two critique passes. Gate: a stranger can complete the claim flow on a phone without help; all screens pass the quality floor.

**Phase 5 — Red-team lab + eval (≤ 10 h).** Fixture collection with me, `run_eval.py`, report, lab screen with live Gemini fake generation. Gate: eval report committed with n and held-out numbers.

**Phase 6 — Hardening + deploy (≤ 6 h).** Rate limits on public endpoints, input size limits, secrets audit, error budgets, judge mode (see below), uptime check, cold-start mitigation (keep-warm ping), cost cap on Gemini calls. Gate: fresh-browser run-through of the judge path passes three times in a row.

**Phase 7 — Submission assets (≤ 8 h).** README, docs, video script + shot list + captions, Devpost text, screenshots, AI tools list. Gate: checklist in §11 fully ticked.

**Phase 8 — Stretch (only with time):** AG Grid claims desk; upstream toolkit issue/PR; Spanish copy for the buyer flow.

**Judge mode:** a public path that needs no PayPal login and no keys: "Try a claim" uses a pre-staged sandbox dispute and a printable/on-screen demo order card, runs the real verifier and the real PayPal actions against our sandbox, and resets nightly. Put demo credentials (sandbox buyer/merchant) in the Devpost "testing instructions", never in the repo.

---

## 10. The video (write `docs/VIDEO_SCRIPT.md`; target 2:45)
- **0:00–0:20 hook:** a real-looking cracked-mug photo appears; "This crack was added by AI in five seconds." Cut to headline facts (WIRED/Forter/the crab case, cited on screen).
- **0:20–0:40 problem + who:** Maya's shop; SNAD isn't covered by PayPal Seller Protection; detectors can't tell.
- **0:40–1:20 the idea, live:** the phone in a real kitchen, the mug glowing through the color sequence, the chromagram filling slot by slot; verdict "Filmed now, under our light. 10 of 10."
- **1:20–1:55 PayPal, live:** console: dispute arrived by webhook, agent's invite sent through the PayPal dispute, policy rule fired, partial refund offer made via the Disputes API, sandbox adjudication; show request IDs.
- **1:55–2:25 the fraudster:** lab: AI-faked photo, old flow accepts it; Proof of Light flow: flat chromagram, "0 of 10 — not filmed under our light"; agent files evidence PDF; adjudicate → seller wins.
- **2:25–2:45 proof + close:** eval numbers with n, architecture in one frame (PayPal + Gemini + Render Workflows), "Liveness for things, not faces." Repo + license on screen.
Rules: real screen recordings only, no stock footage, no third-party logos/music (use silence or self-made/royalty-free-with-license music), captions burned in, readable at 1080p, no loading spinners left in.

---

## 11. Final checklist (all must be true before submitting)
- [ ] Hosted URL works in a fresh incognito window on desktop and phone; judge mode works without login or keys.
- [ ] Repo public, MIT license visible in About; README has: one-line pitch, 20-second GIF of the chromagram, problem with cited sources, how it works (diagram), PayPal APIs used (table with endpoints), AI use (where the model proposes vs where code decides), sponsor usage, eval results with n and reproduce command, threat model summary, limitations, local setup in ≤ 5 commands, judge quick path, AI tools used.
- [ ] Video < 3:00, public on YouTube, human voice, captions, no third-party trademarks/music.
- [ ] Devpost: description, Built With (PayPal Orders v2, Payments v2, Disputes API, Webhooks, Tracking, JS SDK v6, PayPal Agent Toolkit, Gemini, Render Workflows, APIMatic Context Plugin, Kernel), AI tools list, testing instructions with sandbox credentials.
- [ ] APIMatic claim form and Render credit noted; sponsor sections in the README.
- [ ] Every number in README/video traceable to `eval/reports/` or `docs/research/EVIDENCE.md`.
- [ ] No secrets in git history (run a secret scan).
- [ ] Deployment pinned and monitored through 15 Dec.

---

## 12. How you work
- Commit small and often with clear messages; never `git reset --hard` over uncommitted work.
- Keep `docs/PROGRESS.md` updated at each gate: what's done, what's real vs labelled-simulated, open risks, hours used vs budget.
- When blocked by something only I can do, batch the asks into one message with exact steps.
- Prefer boring, proven code paths for everything except the verifier and the chromagram — that's where the craft goes.
- Before declaring any phase done, run its gate, paste the evidence (test output, URL, screenshot path) into PROGRESS.md.
- Read official docs for every external API before coding against it; record doc URLs next to the code that depends on them.
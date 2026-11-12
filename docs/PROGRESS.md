# Progress

## 12 Nov 2026 — Local buyer and merchant workflow

The buyer invitation, optional photo or guided capture, merchant case review, approval and evidence PDF work in the running application. Browser verification used Chromium's simulated camera on disposable SQLite and PostgreSQL databases. Render's published Blueprint schema accepted `render.yaml`. The SDK request and checkout-to-refund tests use stubbed responses. The updated suite passes 63 tests. Browser evidence is in `eval/reports/2026-11-12-review-browser.json` and the practice screenshots are in `design/screenshots/`.

The app now includes sandbox checkout and capture, tracking, dispute listing and verified webhook intake, opt-in Gemini notes, and a separate merchant-authorized USD refund send. The deadline build uses same-origin static JavaScript served by FastAPI and PayPal's hosted approval redirect. It does not use React, JS SDK v6, Agent Toolkit or Render Workflows. Dispute decisions remain in PayPal's Resolution Center. A practice case is available to the authenticated merchant. A public judge flow and live sandbox transactions remain pending.

PayPal and Gemini credentials were absent at verification. Hosted release still needs exact publication approval and a Render workspace. `DEPLOY.md` describes the verification steps and `VIDEO_SCRIPT.md` and `DEVPOST.md` contain recording and submission drafts.

## 8 Nov 2026: approved capture-assistance pivot and review foundation

The user chose: "Revise the pitch to a capture-assistance tool; keep money movement
behind merchant review." Infrastructure work resumes under `PRODUCT_BRIEF.md`.
The original physical/security gate is not retroactively marked passed. The
historical Phase 0 checkpoint below records why the promise changed.

Completed in this checkpoint:
- Revised product pitch, capture screen, README and policy boundaries. No
  automatic denial or fraud accusation from a failed/weak light response.
- Authenticated merchant review API, durable SQLAlchemy case/proposal/approval/
  outbox/audit records and Alembic upgrade/check/downgrade path. Local SQLite only.
- Exact action/amount/currency/destination/version approval, expiry, rejection,
  stale-case invalidation, idempotent repeated approvals and audit hash chaining.
- PayPal SDK 2.4.0 checkout adapter grounded with the installed official APIMatic
  context package. Sandbox-only catalog pricing, OAuth caching, request IDs,
  bounded 429/5xx retries and unknown-outcome handling after transport failure.
- Generated an ignored local `.env` with a merchant-only credential; no external
  sandbox/model keys were generated, displayed or committed.

Evidence: 59 tests pass (one upstream test-client deprecation warning), including
actual SDK serialization over a stubbed HTTP transport, all financial proposal
kinds and migration round-trip. Ruff, formatting, JavaScript syntax and installed
package consistency pass. SDK responses are synthetic; no real transaction was
performed. No live Postgres concurrency test has run.

Phase 1 remains incomplete: public checkout routes/store, tracking, dispute
intake/webhook verification/polling, staged disputes and hosted resources are
not implemented. Refund execution, Gemini, Agent Toolkit and later phases remain
pending. Approval returns AWAITING_EXECUTOR and paypal_executed=false.

External inputs requested: choose Render workspace (My Workspace or mnb) and add
PayPal sandbox client ID/secret plus Gemini key to the existing ignored `.env`.
Do not paste credentials into chat. No Render resources have been created and
there is no production deployment. The prepared `python -m scripts.check_sandbox` only
checks a token exchange once credentials are available; it creates no orders or
financial actions.

Budget: this is the first Phase 1 foundation checkpoint, within the 12-hour phase
budget. Elapsed session time is not treated as a measured engineering benchmark.

## 8 Nov 2026: Phase 0 checkpoint

**Gate NOT PASSED. Later phases have not started.** Physical recordings are
pending. An actual local HTTP probe confirmed that the proposed client-upload
trust boundary permits synthetic injected frames to pass without a camera.

Budget: Phase 0 is capped at six hours in the brief. This first engineering
checkpoint used less than one hour of elapsed session time; this is an
estimate, not a measured engineering labor benchmark. No later-phase budget,
cloud spend or model spend has been used. Do not imply all-day monitoring or
unattended work after this chat turn ends.

### Implemented and real
- Local server and consented camera workbench with standard/reduced illumination.
- Signed CSPRNG challenge, TTL, single use, same-origin/host restrictions and
  upload bounds. The process secret and challenge records are not durable.
- Frame sampling, rAF mutation log, device metadata and condition labels.
- Provisional deterministic verifier, chromagram, trace, heatmap and NPZ export.
- Offline CLI, JSON recovery tool, physical recording protocol and gate runner.
- MIT license, build brief, design plan, source references, test workflow and docs.

### Evidence
- `.venv/bin/python -m pytest -q`: **23 passed**, one upstream test-client
  deprecation warning. The tests use synthetic data, not physical recordings.
- Ruff checks and formatting, JavaScript syntax, and dependency consistency pass.
- Fake-camera Playwright QA: full capture -> analysis -> result -> NPZ download;
  consent, Escape cancellation, alternative path and camera-denied recovery.
  No horizontal overflow at 360/390/768 px. No JavaScript page errors in the final run.
  Report: `eval/reports/2026-11-08-browser-final.json`.
- Offline CLI reanalyzed `/tmp/pol-browser-fake-camera.npz`: INCONCLUSIVE, as
  expected for fake media that does not receive the changing screen light.
- Reproduction: `.venv/bin/python scripts/probe_injection.py` against the local
  service. Saved run: VERIFIED, 10/10, correlation 0.9812927, without a camera.
  Report: `eval/reports/2026-11-08-injection.json`. A second probe against the
  final server also bypassed it with 10/10; saved in `2026-11-08-injection-final.json`.
  These are individual laptop runs, not performance or security benchmarks.
- Screenshots: `design/screenshots/pass1-*`, `pass2-*`, `final-*`; two revisions and critique in DESIGN_PLAN.

### What is synthetic or absent
All numerical fixtures, injection pixels and automated browser media are
synthetic and labeled. Zero physical experiment recordings have been supplied.
PayPal, Gemini, Agent Toolkit, APIMatic, Render, Kernel, durable claims, evidence
PDFs, judge mode and the production frontend are not implemented. No hosted
URL, refunds, dispute closure, submission, sponsor claim or measured FAR/FRR.
CI configuration exists; no remote CI result has been observed.

### Why the gate cannot be declared passed
1. Need the actual 3-object x 3-light x 2-device capture matrix and three physical
   attacks. See `scripts/record_fixture.md`. No fabricated physical fixtures.
2. A printed photo can reflect illumination; expected rejection is unproven.
3. A client can read the challenge and synthesize matching uploaded pixels and
   timing. HMAC/TTL/nonce checks do not address this; the local probe reproduces it.
4. The 20-bit guessing null is irrelevant to that adaptive attack.

### User direction needed
The original anti-injection promise cannot be supported by this implementation.
Choose either a narrower capture-assistance product with merchant-reviewed money
movement, or further investigation of trusted capture before building the PayPal
product. Physical optics tests are still useful for either investigation, but
passing them alone would not resolve this security failure.

Do not progress to Phase 1 or connect this verdict to an autonomous refund while
presenting it as fraud protection. This follows the user's explicit Phase 0
stop/report requirement and the honesty rules, not a new approval requirement.

### Saved checkpoint
Implementation is saved in local commit `5ee0578`; documentation, screenshots
and reports are saved in the following checkpoint commit. Gitleaks found no
leaks in staged source, staged documentation or the initial commit history.
No remote push or production deployment was performed. The local workbench
remains available at http://127.0.0.1:8000 while its server session is running.

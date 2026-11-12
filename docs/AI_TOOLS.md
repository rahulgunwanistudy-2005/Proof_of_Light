# AI tools used and how

## Phase 0
- Codex: interpreted the user-supplied session prompt, created the experimental
  browser capture and Python verifier, wrote numerical/API/browser checks,
  reviewed screenshots and documented the adaptive-upload bypass.
- Firecrawl plugin: retrieved official MDN, NumPy, FastAPI and W3C references for
  secure camera access, video timing, numeric exports, body validation and
  flashing guidance. Sources are listed in `docs/REFERENCES.md`.
- Frontend-design skill: the supplied local skill informed the design plan and
  screenshot critique workflow; it is retained with its own license.
- Webapp-testing skill: informed fake-camera Playwright smoke testing and visual
  review. Automated tests never accessed the user's physical camera.

No generative images or videos were used. Synthetic numerical signal fixtures
and the injection probe are labeled test data, not physical experiments.

## APIMatic used for the checkout foundation
Installed the official PayPal context package from
https://github.com/paypaldev/server-sdk-context-plugin-preview at commit
`6aa057126f0d4709a42e15002aab832a94935d92` using the published context-plugins
installer for Codex. The installer confirmed `paypal@context-plugins-local`.
It advises a new Codex session to auto-load skills. In this session the installed
Python skills were read explicitly from its installed cache before coding.

Read python-getting-started, client-initialization, authentication,
calling-endpoints, models, error-handling, configuration-resilience and testing.
Installed the specified paypal-server-sdk 2.4.0 and inspected that installed
source to confirm method shapes, auth credentials, enum-to-host mapping and models.

Concrete effects in `apps/api/paypal/checkout.py` and its tests:
- Uses `PaypalServersdkClient`, explicit `Environment.SANDBOX`, flat timeout/retry
  options and `ClientCredentialsAuthCredentials`; avoids an obsolete SDK.
- Calls `client.orders.create_order/get_order/capture_order` with the actual
  single options-dictionary shape, not guessed keyword signatures.
- Builds `OrderRequest.from_dictionary` from wire-named catalog fields and reads
  the real ApiResponse envelope. Retry policy is one application layer; SDK
  retries stay off, and transport errors produce an unknown-outcome state.
- Tests below the SDK using a URL-routed requests adapter. OAuth succeeds before
  operation-specific failures, so negative tests exercise checkout rather than
  accidentally failing only the token exchange.

No fabricated before/after comparison or sponsor prize eligibility is claimed.
SDK wire behavior is locally stub-tested; real sandbox behavior is pending keys.
The first SDK install failed resolving msgpack; installing its compatible 1.2.4
wheel and retrying succeeded. No SDK source was edited or vendored.

## Still planned
Gemini, PayPal Agent Toolkit, Kernel and Render Workflows are not yet used.
Render workspace discovery found two workspaces; user selection is pending and
no resources have been created. No outreach or external message was sent.

## 12 Nov 2026 workflow build

Codex used the installed PayPal Python skills and SDK source to wire sandbox checkout, tracking and refund payloads. Firecrawl retrieved official PayPal, Gemini and Render documentation. Built-in ImageGen produced `apps/spike/catalog-ceramics.png`, a triptych of a misty blue mug, olive bowl and sand-pink plate under diffused studio light. The app uses the contact sheet for sandbox catalog illustrations.

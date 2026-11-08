# Merchant review contract

The approved product is capture assistance. A light-response result is never an
authorization to refund, make a refund offer, accept a claim or commit a return.
AI is not connected yet; when added it may propose actions, not approve them.

## Implemented local API

All `/api/review/*` routes require a merchant-only bearer credential. A server
operator configures one merchant ID and token in the ignored `.env`; no default
credential or buyer token is accepted. This is a local single-merchant foundation,
not a completed multi-tenant login/session system.

| Route | Behavior |
| --- | --- |
| `POST /api/review/cases` | Save a manually supplied case snapshot; not a PayPal intake event |
| `GET /api/review/cases` | List the authenticated merchant's cases |
| `GET /api/review/cases/{id}` | Read snapshot, proposals, queue and audit chain |
| `PUT /api/review/cases/{id}` | Update at an expected version; invalidate prior proposals/queued approvals |
| `POST /api/review/cases/{id}/proposals` | Validate amount/currency/destination and create PENDING_REVIEW |
| `POST /api/review/proposals/{id}/approve` | Require explicit confirmation, exact payload hash and case version; save approval and outbox atomically |
| `POST /api/review/proposals/{id}/reject` | Record merchant rejection of a pending proposal |

Approvals expire with the proposal after 15 minutes. Repeated approval clicks
reuse the same queue entry. Rejected/expired/invalidated proposals cannot be
approved. Changes in case inputs, amount, currency, destination or action cannot
reuse the previous approval. The actor comes from authenticated server state,
never the request body. Every financial action type currently requires review.

**An approved queue entry is not a PayPal result.** It remains AWAITING_EXECUTOR
and the response explicitly says `paypal_executed: false`. No refund executor or
automatic action is implemented. The checkout SDK adapter is not connected to
this outbox and does not expose a refund method.

## Try the API locally

1. Run `scripts/init_local.py`, then `alembic upgrade head` using the project
   environment as shown in README. The helper never overwrites an existing `.env`.
2. Keep the merchant token private. In the local `/docs` page, use Authorize to
   provide it. Do not put that credential in public testing instructions or buyer
   pages. Without merchant auth, review endpoints return 401; missing server
   configuration returns 503.
3. Enter a manually labeled case using a test order/capture/dispute ID, integer
   minor amount and three-letter currency. It is local review data, not proof
   that PayPal knows that order. Create a proposal and inspect its exact payload.
4. Approve only after reviewing the payload hash and current case version. The
   API will save the intent and report that PayPal has not executed it.

## Eventual executor requirements

The future PayPal executor must call `ready_action` immediately before a request
and preserve the case lock through the action, so concurrent edits cannot make
approval stale during dispatch. It must also validate fresh PayPal ownership,
stage, balance, allowed action, currency and remaining refundable amount; those
external checks are not implemented by the local approval package.

Use the stored request ID for every retry and reconcile unknown outcomes before
issuing a new operation. Do not infer success from an approval or a timeout.
AI tooling must not receive the merchant credential or expose the approve route
as an autonomous tool. Authenticated account control is not camera attestation
or a cryptographic proof that a human saw a particular screen.

## Storage and limits

Case/proposal/approval/outbox/audit records persist in SQLite locally. Alembic
creates the schema; requests never silently initialize tables. A Postgres driver
and URL conversion are prepared; live Postgres concurrency has not been tested.
Postgres uses case-row locks; queue/proposal/approval uniqueness provides another
guard against duplicate entries. The audit chain is per case and detects
inconsistency when checked, but has no external immutable anchor.

Capture frames still use the separate ten-minute in-memory Phase 0 store.
Durable review records do not expire automatically. Production data retention,
backups, tenant login, worker dispatch and public deployment remain unfinished.

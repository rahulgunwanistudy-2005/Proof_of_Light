# Merchant review contract

The merchant credential authorizes case management and approval. The buyer invitation authorizes one evidence submission for its case. Evidence and AI notes are advisory. Financial action starts with an explicit merchant proposal.

## Approval and dispatch

1. The proposal records action, amount in minor units, currency and PayPal destination. It includes a digest of that payload and the current case version.
2. The merchant confirms the exact details. A transaction saves the approval, outbox row and audit event. Repeated approval calls return the same outbox row.
3. Sending is a separate merchant action. The server validates approval expiry, payload digest, actor, case version and a current PayPal order that contains the matching completed capture. The request uses the recorded idempotency key. A unique capture reservation prevents another refund attempt through this app.
4. A confirmed PayPal completion records its refund ID. Pending, rejected and uncertain responses have distinct states. Check PayPal before taking further action on uncertain or pending requests.

New buyer evidence and AI notes change the case revision and invalidate unsent proposals. The direct integration handles USD refunds for eligible captures. Imported disputes are reviewed in Proof of Light and resolved in PayPal’s Resolution Center. Practice cases use fabricated references and can be approved locally.

## Data and access

Buyer links carry an opaque token in the URL fragment. The database stores its hash, expiry and use time. A new link expires older unused invitations for the case. The submitted JPEG is re-encoded to remove metadata. Merchant access is required for viewing evidence and downloading the PDF. AI notes use an image and statement only after opt-in. They do not propose or send a payment.

Audit entries link each event digest to the preceding digest. This supports review of the stored sequence. The local deployment uses one merchant credential and does not implement identity federation or a retention service. Configure an appropriate access and retention policy before collecting customer evidence beyond the sandbox.
